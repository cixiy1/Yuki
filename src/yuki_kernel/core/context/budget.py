"""上下文预算与摘要。"""

import asyncio
import math
from typing import Any, Callable, Optional

from ...config import Settings
from ..errors import ProviderError
from ..memory import MemoryStore

MemoryProvider = Callable[[], list[dict[str, Any]]]
Chat = Callable[..., Any]
SessionIdProvider = Callable[[], str]


class ContextManager:
    def __init__(
        self,
        settings: Settings,
        memory_provider: MemoryProvider,
        chat: Chat,
        memory_store: Optional[MemoryStore],
        session_id_provider: SessionIdProvider,
    ):
        self.settings = settings
        self.memory_provider = memory_provider
        self.chat = chat
        self.memory_store = memory_store
        self.session_id_provider = session_id_provider

    def estimate(self) -> int:
        total = 0
        for message in self.memory_provider():
            content = message.get("content") or ""
            total += max(1, math.ceil(len(content) / 3)) + 4
        return total

    async def ensure(self) -> None:
        if self.settings.max_context_tokens <= 0:
            return
        for _ in range(3):
            if self.estimate() <= self.settings.max_context_tokens:
                return
            if not await self._summarize_oldest():
                self._drop_oldest()

    async def _summarize_oldest(self) -> bool:
        memory = self.memory_provider()
        keep = self.settings.keep_recent_messages
        if len(memory) - 1 <= keep:
            return False
        target = [
            message
            for message in memory[1 : len(memory) - keep]
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
        except (ProviderError, ConnectionError, TimeoutError, OSError):
            return False
        if not summary.strip():
            return False
        memory[1 : len(memory) - keep] = [
            {"role": "system", "content": "[历史摘要] " + summary.strip()}
        ]
        if self.memory_store is not None:
            await asyncio.to_thread(
                self.memory_store.add,
                self.session_id_provider(),
                "摘要：" + summary.strip(),
            )
        return True

    async def _collect(self, messages: list[dict[str, Any]]) -> str:
        parts = []
        async for chunk in self.chat(messages, tools=None):
            if chunk.content:
                parts.append(chunk.content)
        return "".join(parts)

    def _drop_oldest(self) -> None:
        memory = self.memory_provider()
        for index, message in enumerate(memory):
            if message.get("role") in {"user", "assistant"}:
                memory.pop(index)
                return
