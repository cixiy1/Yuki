"""工具闭环契约：单次工具调用。"""

import pytest

from yuki.cli import Response
from yuki.providers import ChatChunk
from yuki.skills import ToolRegistry
from yuki.core.agent import Agent

from tests.fake_provider import FakeProvider, env_tool_call_chunk


@pytest.mark.asyncio
async def test_tool_loop(settings):
    registry = ToolRegistry(None)
    fake = FakeProvider(
        script=[
            [env_tool_call_chunk()],
            [ChatChunk(content="环境信息已返回。"), ChatChunk(done=True)],
        ],
        settings=settings,
    )
    agent = Agent("fake", registry, settings, provider=fake)

    out = Response(agent.send_message("看看环境"))
    events = []
    while True:
        event = await out.next_event()
        if event is None:
            break
        events.append(event)
    assert any(event["type"] == "tool_calls" for event in events)

    results = await agent.execute_tool_calls(out.tool_calls)
    assert "操作系统" in results[0]["content"]

    out = Response(agent.continue_with_tools(out.tool_calls, results))
    text = ""
    while True:
        event = await out.next_event()
        if event is None:
            break
        if event["type"] == "content":
            text += event["text"]
    assert "环境信息" in text
