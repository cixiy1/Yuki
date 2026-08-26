"""工具闭环契约：turn_stream 事件。"""

import pytest

from yuki_kernel.core.agent import Agent
from yuki_kernel.providers import ChatChunk
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


@pytest.mark.asyncio
async def test_list_packages_then_concrete_tool(settings, weather_package):
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
