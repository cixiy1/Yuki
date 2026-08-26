"""脚本化 FakeProvider，用于契约测试。"""

from typing import Any, AsyncIterator

from yuki_kernel.config import Settings
from yuki_kernel.providers import ChatChunk, Provider


class FakeProvider(Provider):
    def __init__(
        self,
        settings: Settings,
        script: Any = None,
        model: str = "fake",
        errors: Any = None,
    ):
        super().__init__(model, settings)
        self.script = list(script or [])
        self.errors = list(errors or [])
        self.calls = 0
        self.closed = False

    async def close(self, skip_unload: bool = False):
        self.closed = True

    async def chat(
        self,
        messages,
        tools=None,
        **kwargs,
    ) -> AsyncIterator[ChatChunk]:
        del messages, tools, kwargs
        if self.calls < len(self.errors):
            err = self.errors[self.calls]
            self.calls += 1
            raise err
        chunks = self.script[min(self.calls, len(self.script) - 1)] if self.script else []
        self.calls += 1
        for chunk in chunks:
            yield chunk

    @staticmethod
    def build_tool_messages(
        tool_calls,
        results,
    ):
        assistant = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": call["name"], "arguments": call["arguments"]}}
                for call in tool_calls
            ],
        }
        return [
            assistant,
            *[{"role": "tool", "content": r["content"]} for r in results],
        ]


def env_tool_call_chunk() -> ChatChunk:
    return ChatChunk(
        tool_calls=[
            {
                "index": 0,
                "id": "call_1",
                "function": {
                    "name": "get_environment_info",
                    "arguments": "{}",
                },
            }
        ]
    )
