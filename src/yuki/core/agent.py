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
        self.memory = list(memory or [])
        if system_prompt and (not self.memory or self.memory[0].get("role") != "system"):
            self.memory.insert(0, {"role": "system", "content": system_prompt})
        self.provider = create_provider(provider, model, **provider_kwargs)

    def start(self):
        return self.provider.start()

    def close(self, skip_unload: bool = False):
        return self.provider.close(skip_unload=skip_unload)

    def send_message(self, user_message: str) -> Iterator[ChatChunk]:
        self.memory.append({"role": "user", "content": user_message})
        return self.provider.chat(self.memory, tools=self.registry.tools)

    def execute_tool_calls(self, tool_calls: list[Any]) -> list[dict[str, Any]]:
        return execute_tool_calls(self.registry, tool_calls)

    def continue_with_tools(
        self,
        tool_calls: list[Any],
        results: list[dict[str, Any]],
    ) -> Iterator[ChatChunk]:
        calls = merge_tool_calls(tool_calls)
        self.memory.extend(self.provider.build_tool_messages(calls, results))
        return self.provider.chat(self.memory, tools=self.registry.tools)
