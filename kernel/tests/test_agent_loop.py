"""工具闭环契约：turn_stream 事件。"""

import pytest

from yuki_kernel.config import Settings
from yuki_kernel.core.agent import Agent
from yuki_kernel.providers import ChatChunk, Provider
from yuki_kernel.skills import ToolRegistry

# noinspection PyUnresolvedReferences
from yuki_kernel.testing import FakeProvider, env_tool_call_chunk


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


@pytest.mark.asyncio
async def test_turn_auto_loads_available_package(settings, weather_package):
    registry = ToolRegistry(weather_package, available=["weather"])
    fake = FakeProvider(
        script=[
            [
                ChatChunk(
                    tool_calls=[
                        {
                            "index": 0,
                            "id": "call_1",
                            "function": {
                                "name": "weather_now",
                                "arguments": '{"city":"New York"}',
                            },
                        }
                    ]
                )
            ],
            [ChatChunk(content="纽约 22°C。"), ChatChunk(done=True)],
        ],
        settings=settings,
    )
    agent = Agent("fake", registry, settings, provider=fake)

    texts = []
    async for event in agent.turn_stream("纽约天气"):
        if event.kind == "tool_result":
            texts.append(event.text)

    assert "22°C" in texts
    assert registry.active_packages == []


class _LoopProvider(Provider):
    def __init__(self, settings: Settings, names: list[str]):
        super().__init__("loop", settings)
        self.tool_calls = 0
        self.names = names

    async def chat(self, messages, tools=None, **kwargs):
        del messages, kwargs
        if tools is None:
            yield ChatChunk(content="最终回答")
            yield ChatChunk(done=True)
            return
        name = self.names[self.tool_calls % len(self.names)]
        self.tool_calls += 1
        yield ChatChunk(
            tool_calls=[
                {
                    "index": 0,
                    "id": f"call_{self.tool_calls}",
                    "function": {
                        "name": name,
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
async def test_repeated_tool_calls_stop_early(settings):
    registry = ToolRegistry(None)
    provider = _LoopProvider(settings, names=["get_environment_info"])
    agent = Agent("loop", registry, settings, provider=provider)

    events = []
    async for event in agent.turn_stream("一直调用工具"):
        events.append((event.kind, event.text))

    assert provider.tool_calls == 3
    assert any(kind == "content" and "最终回答" in text for kind, text in events)
    assert any(
        message.get("role") == "system"
        and "直接调用包内具体工具" in message.get("content", "")
        for message in agent.memory
    )
    assert any(
        message.get("role") == "system"
        and "用户刚才的问题是" in message.get("content", "")
        and "最近一次工具结果" in message.get("content", "")
        for message in agent.memory
    )


@pytest.mark.asyncio
async def test_repeated_meta_call_recovers_to_real_tool(settings, weather_package):
    registry = ToolRegistry(weather_package, available=["weather"])
    list_call = {
        "index": 0,
        "id": "call_list",
        "function": {"name": "list_packages", "arguments": "{}"},
    }
    weather_call = {
        "index": 0,
        "id": "call_weather",
        "function": {"name": "weather_now", "arguments": '{"city":"New York"}'},
    }
    fake = FakeProvider(
        script=[
            [ChatChunk(tool_calls=[list_call])],
            [ChatChunk(tool_calls=[list_call])],
            [ChatChunk(tool_calls=[weather_call])],
            [ChatChunk(content="纽约 22°C。"), ChatChunk(done=True)],
        ],
        settings=settings,
    )
    agent = Agent("fake", registry, settings, provider=fake)

    results = []
    content = ""
    async for event in agent.turn_stream("纽约天气"):
        if event.kind == "tool_result":
            results.append(event.text)
        if event.kind == "content":
            content += event.text

    assert any("22°C" in text for text in results)
    assert "纽约 22°C。" in content
    assert registry.active_packages == []


@pytest.mark.asyncio
async def test_tool_loop_is_bounded(settings):
    registry = ToolRegistry(None)
    provider = _LoopProvider(
        settings,
        names=["get_environment_info", "list_packages"],
    )
    agent = Agent("loop", registry, settings, provider=provider)

    events = []
    async for event in agent.turn_stream("一直调用工具"):
        events.append((event.kind, event.text))

    assert provider.tool_calls == settings.max_tool_rounds + 1
    assert any(kind == "content" and "最终回答" in text for kind, text in events)
