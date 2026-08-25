"""示例测试用的最小 FakeProvider。"""

from typing import Any, AsyncIterator

# noinspection PyUnresolvedReferences
from yuki_kernel.config import Settings
# noinspection PyUnresolvedReferences
from yuki_kernel.providers import ChatChunk, Provider


class FakeProvider(Provider):
    def __init__(
        self,
        settings: Settings,
        script: Any = None,
        model: str = "fake",
    ):
        super().__init__(model, settings)
        self.script = list(script or [])
        self.calls = 0

    async def chat(
        self,
        messages,
        tools=None,
        **kwargs,
    ) -> AsyncIterator[ChatChunk]:
        del messages, tools, kwargs
        chunks = self.script[min(self.calls, len(self.script) - 1)] if self.script else []
        self.calls += 1
        for chunk in chunks:
            yield chunk

    @staticmethod
    def build_tool_messages(
        tool_calls,
        results,
    ):
        del tool_calls, results
        return []
