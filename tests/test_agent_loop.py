"""工具闭环契约：单次工具调用。"""

import pytest

from yuki.cli import Response
from yuki.providers import ChatChunk
from yuki.skills import ToolRegistry
from yuki.core.agent import Agent

from tests.fake_provider import FakeProvider


@pytest.mark.asyncio
async def test_tool_loop(settings):
    registry = ToolRegistry(None)
    fake = FakeProvider(
        script=[
            [
                ChatChunk(
                    tool_calls=[
                        {
                            "index": 0,
                            "id": "call_1",
                            "function": {
                                "name": "get_name",
                                "arguments": '{"name": "张三"}',
                            },
                        }
                    ]
                )
            ],
            [ChatChunk(content="张三的家庭在纽约。"), ChatChunk(done=True)],
        ],
        settings=settings,
    )
    agent = Agent("fake", registry, settings, provider=fake)

    out = Response(agent.send_message("张三家"))
    events = []
    while True:
        event = await out.next_event()
        if event is None:
            break
        events.append(event)
    assert any(event["type"] == "tool_calls" for event in events)

    results = await agent.execute_tool_calls(out.tool_calls)
    assert results[0]["content"] == "纽约"

    out = Response(agent.continue_with_tools(out.tool_calls, results))
    text = ""
    while True:
        event = await out.next_event()
        if event is None:
            break
        if event["type"] == "content":
            text += event["text"]
    assert "纽约" in text
