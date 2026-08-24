from typing import Any, Iterator, Optional

from ..providers import ChatChunk, create_provider
from ..skills import ToolRegistry
from .tools import execute_tool_calls, merge_tool_calls


class Agent:
    def __init__(
        self,
        model: str,
        registry: ToolRegistry,
        provider: str = "ollama",
        memory: Optional[list[dict[str, Any]]] = None,
        system_prompt: str = "",
        **provider_kwargs,
    ):
        self.model = model
        self.registry = registry
        self.system_prompt = system_prompt
        self.memory = list(memory or [])
        self._sync_system_prompt()
        self.provider = create_provider(provider, model, **provider_kwargs)

    def _sync_system_prompt(self):
        """按当前已加载的工具包重写系统消息。"""
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

    def start(self):
        return self.provider.start()

    def close(self, skip_unload: bool = False):
        return self.provider.close(skip_unload=skip_unload)

    def send_message(self, user_message: str) -> Iterator[ChatChunk]:
        self.memory.append({"role": "user", "content": user_message})
        return self.provider.chat(self.memory, tools=self.registry.tools)

    def execute_tool_calls(self, tool_calls: list[Any]) -> list[dict[str, Any]]:
        results = execute_tool_calls(self.registry, tool_calls)
        self._sync_system_prompt()
        return results

    def restore_packages(self, package_ids: list[str]) -> list[str]:
        """还原外置包状态，并同步系统消息。"""
        changed = self.registry.restore_packages(package_ids)
        self._sync_system_prompt()
        return changed

    def continue_with_tools(
        self,
        tool_calls: list[Any],
        results: list[dict[str, Any]],
    ) -> Iterator[ChatChunk]:
        calls = merge_tool_calls(tool_calls)
        self.memory.extend(self.provider.build_tool_messages(calls, results))
        return self.provider.chat(self.memory, tools=self.registry.tools)
