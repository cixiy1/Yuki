from typing import Any, Iterator, Optional

from ..providers import ChatChunk, create_provider
from ..skills import Skills
from .tools import execute_tool_calls, merge_tool_calls


class Agent:
    def __init__(
        self,
        model: str,
        skill: Skills,
        provider: str = "ollama",
        memory: Optional[list[dict[str, Any]]] = None,
        **provider_kwargs,
    ):
        self.model = model
        self.skill = skill
        self.memory: list[dict[str, Any]] = memory or []
        self.provider = create_provider(provider, model, **provider_kwargs)

    def start(self):
        return self.provider.start()

    def close(self, skip_unload: bool = False):
        return self.provider.close(skip_unload=skip_unload)

    def send_message(self, user_message: str) -> Iterator[ChatChunk]:
        self.memory.append({"role": "user", "content": user_message})
        return self.provider.chat(self.memory, tools=self.skill.tools)

    def execute_tool_calls(self, tool_calls: list[Any]) -> list[dict[str, Any]]:
        return execute_tool_calls(self.skill, tool_calls)

    def continue_with_tools(
        self,
        tool_calls: list[Any],
        results: list[dict[str, Any]],
    ) -> Iterator[ChatChunk]:
        calls = merge_tool_calls(tool_calls)
        self.memory.extend(self.provider.build_tool_messages(calls, results))
        return self.provider.chat(self.memory, tools=self.skill.tools)
