"""工具闭环契约：turn_stream 事件。"""

import pytest

from yuki_kernel.config import Settings
from yuki_kernel.core.agent import Agent
from yuki_kernel.providers import ChatChunk, Provider
from yuki_kernel.skills import ToolRegistry

from tests.fake_provider import FakeProvider, env_tool_call_chunk


@pytest.mark.asyncio
async def test_turn_stream_tool_loop(settings):
    registry = ToolRegistry(None)
    fake = FakeProvider(
        script=[
            [env_tool_call_chunk()],
            [ChatChunk(content="环境信息已返回。"), ChatChunk(done=True)],
        ],
        settings=settings,
    )
    agent = Agent("fake", registry, settings, provider=fake)

    kinds = []
    content = ""
    async for event in agent.turn_stream("看看环境"):
        kinds.append(event.kind)
        if event.kind == "content":
            content += event.text

    assert "tool_calls" in kinds
    assert "tool_result" in kinds
    assert "环境信息" in content


class _LoopProvider(Provider):
    def __init__(self, settings: Settings):
        super().__init__("loop", settings)
        self.tool_calls = 0

    async def chat(self, messages, tools=None, **kwargs):
        del messages, kwargs
        if tools is None:
            yield ChatChunk(content="最终回答")
            yield ChatChunk(done=True)
            return
        self.tool_calls += 1
        yield ChatChunk(
            tool_calls=[
                {
                    "index": 0,
                    "id": "call_loop",
                    "function": {
                        "name": "get_environment_info",
                        "arguments": "{}",
                    },
                }
            ]
        )
        yield ChatChunk(done=True)

    @staticmethod
    def build_tool_messages(tool_calls, results):
        return [
            {"role": "assistant", "content": "", "tool_calls": tool_calls},
            *[{"role": "tool", "content": result["content"]} for result in results],
        ]


@pytest.mark.asyncio
async def test_tool_loop_is_bounded(settings, tmp_path):
    registry = ToolRegistry(None)
    provider = _LoopProvider(settings)
    agent = Agent("loop", registry, settings, provider=provider)

    events = []
    async for event in agent.turn_stream("一直调用工具"):
        events.append((event.kind, event.text))

    assert provider.tool_calls == settings.max_tool_rounds + 1
    assert any(kind == "content" and "最终回答" in text for kind, text in events)
