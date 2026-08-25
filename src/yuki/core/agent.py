"""Agent：异步会话闭环，包含重试、摘要、审批与钩子。"""

import asyncio
import math
from typing import Any, AsyncIterator, Awaitable, Callable, Optional, Union

from ..config import Settings
from ..providers import ChatChunk, Provider, create_provider
from ..skills import ToolRegistry
from .bus import EventBus
from .errors import is_transient
from .events import AgentEvent
from .middleware import Middleware, run_after, run_before
from .session import Session
from .tools import merge_tool_calls

Approver = Callable[[str, dict[str, Any]], Awaitable[str]]


class Agent:
    def __init__(
        self,
        model: str,
        registry: ToolRegistry,
        settings: Settings,
        session: Optional[Session] = None,
        provider: Union[str, Provider] = "ollama",
        system_prompt: str = "",
        middlewares: Optional[list[Middleware]] = None,
        bus: Optional[EventBus] = None,
        approver: Optional[Approver] = None,
        **provider_kwargs,
    ):
        self.model = model
        self.settings = settings
        self.registry = registry
        self.session = session or Session()
        self.system_prompt = system_prompt
        self.memory = self.session.messages
        self.middlewares = list(middlewares or [])
        self.bus = bus or EventBus()
        self.approver = approver
        if isinstance(provider, Provider):
            self.provider = provider
        else:
            self.provider = create_provider(provider, model, settings)
        self._sync_system_prompt()

    def _sync_system_prompt(self):
        parts = [self.system_prompt] if self.system_prompt else []
        registry_prompt = self.registry.system_prompt()
        if registry_prompt:
            parts.append(registry_prompt)
        content = "\n\n".join(parts)
        if content:
            message = {"role": "system", "content": content}
            if self.memory and self.memory[0].get("role") == "system":
                self.memory[0] = message
            else:
                self.memory.insert(0, message)
        elif self.memory and self.memory[0].get("role") == "system":
            self.memory.pop(0)

    async def _emit(self, kind: str, payload: Any, **context: Any) -> AgentEvent:
        event = AgentEvent(kind=kind, payload=payload, context=context)
        event = await run_before(self.middlewares, event)
        await self.bus.publish(event)
        await run_after(self.middlewares, event)
        return event

    async def start(self):
        await self._emit("session_start", self.session)
        return await self.provider.start()

    async def close(self, skip_unload: bool = False):
        await self._emit("session_end", self.session)
        return await self.provider.close(skip_unload=skip_unload)

    def switch_session(self, session: Session) -> None:
        self.session = session
        self.memory = session.messages
        self._sync_system_prompt()

    async def send_message(self, user_message: str) -> AsyncIterator[ChatChunk]:
        event = await self._emit("user_message", user_message)
        if event.context.get("abort"):
            return
        self.memory.append({"role": "user", "content": user_message})
        await self._ensure_context_budget()
        await self._emit("before_model", {"messages": self.memory, "tools": self.registry.tools})
        async for chunk in self._chat_with_retry(self.memory, tools=self.registry.tools):
            await self._emit("assistant_chunk", chunk)
            yield chunk

    async def continue_with_tools(
        self,
        tool_calls: list[Any],
        results: list[dict[str, Any]],
    ) -> AsyncIterator[ChatChunk]:
        calls = merge_tool_calls(tool_calls)
        self.memory.extend(self.provider.build_tool_messages(calls, results))
        await self._ensure_context_budget()
        await self._emit("before_model", {"messages": self.memory, "tools": self.registry.tools})
        async for chunk in self._chat_with_retry(self.memory, tools=self.registry.tools):
            await self._emit("assistant_chunk", chunk)
            yield chunk

    async def execute_tool_calls(self, tool_calls: list[Any]) -> list[dict[str, Any]]:
        results = []
        for call in merge_tool_calls(tool_calls):
            event = await self._emit("tool_call", call)
            if event.context.get("abort"):
                content = "用户已中止"
            elif not await self._check_approval(call["name"]):
                content = "用户拒绝执行"
            else:
                content = await asyncio.to_thread(
                    self.registry.execute,
                    call["name"],
                    call["arguments"],
                )
            results.append({"role": "tool", "name": call["name"], "content": content})
            await self._emit("tool_result", {"name": call["name"], "content": content})
        self._sync_system_prompt()
        return results

    async def restore_packages(self, package_ids: list[str]) -> list[str]:
        changed = self.registry.restore_packages(package_ids)
        for package_id in changed:
            kind = "package_load" if package_id in self.registry.active_packages else "package_unload"
            await self._emit(kind, package_id)
        self._sync_system_prompt()
        return changed

    async def _check_approval(self, name: str) -> bool:
        if not self.registry.needs_approval(name):
            return True
        if self.session.is_approved(name):
            return True
        if self.approver is None:
            return False
        answer = (await self.approver(name, {})).strip()
        if answer == "ya":
            self.session.approve(name)
            return True
        if answer.startswith("y"):
            rest = answer[1:].strip()
            if rest.isdigit():
                self.session.approve(name, int(rest))
            return True
        return False

    async def _chat_with_retry(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> AsyncIterator[ChatChunk]:
        for attempt in range(self.settings.retry_max):
            try:
                async for chunk in self.provider.chat(messages, tools=tools):
                    yield chunk
                return
            except Exception as err:
                if not is_transient(err) or attempt + 1 >= self.settings.retry_max:
                    raise
                await asyncio.sleep(self.settings.retry_base * (2**attempt))

    @staticmethod
    def estimate_tokens(messages: list[dict[str, Any]]) -> int:
        total = 0
        for message in messages:
            content = message.get("content") or ""
            total += max(1, math.ceil(len(content) / 3)) + 4
        return total

    async def _ensure_context_budget(self) -> None:
        if self.settings.max_context_tokens <= 0:
            return
        for _ in range(3):
            if self.estimate_tokens(self.memory) <= self.settings.max_context_tokens:
                return
            if not await self._summarize_oldest():
                self._drop_oldest()

    async def _summarize_oldest(self) -> bool:
        keep = self.settings.keep_recent_messages
        if len(self.memory) - 1 <= keep:
            return False
        target = [
            message
            for message in self.memory[1 : len(self.memory) - keep]
            if not (
                message.get("role") == "system"
                and str(message.get("content", "")).startswith("[历史摘要]")
            )
        ]
        if not target:
            return False
        prompt = [
            {"role": "system", "content": "把以下对话压缩成简洁中文摘要，保留关键事实、结论和未完成事项。"},
            *target,
        ]
        try:
            summary = await self._collect(prompt)
        except Exception:
            return False
        if not summary.strip():
            return False
        self.memory[1 : len(self.memory) - keep] = [
            {"role": "system", "content": "[历史摘要] " + summary.strip()}
        ]
        return True

    async def _collect(self, messages: list[dict[str, Any]]) -> str:
        parts = []
        async for chunk in self._chat_with_retry(messages, tools=None):
            if chunk.content:
                parts.append(chunk.content)
        return "".join(parts)

    def _drop_oldest(self) -> None:
        for index, message in enumerate(self.memory):
            if message.get("role") in {"user", "assistant"}:
                self.memory.pop(index)
                return
