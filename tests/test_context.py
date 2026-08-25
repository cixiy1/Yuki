"""上下文摘要契约。"""

import pytest

from yuki.core.agent import Agent
from yuki.providers import ChatChunk
from yuki.skills import ToolRegistry

from tests.fake_provider import FakeProvider


@pytest.mark.asyncio
async def test_summarize_oldest(settings):
    settings.max_context_tokens = 60
    settings.keep_recent_messages = 1
    fake = FakeProvider(
        script=[[ChatChunk(content="这是历史摘要。")]],
        settings=settings,
    )
    agent = Agent("fake", ToolRegistry(None), settings, provider=fake)
    agent.memory.append({"role": "user", "content": "a" * 100})
    agent.memory.append({"role": "assistant", "content": "b" * 100})
    agent.memory.append({"role": "user", "content": "最近消息"})

    await agent._ensure_context_budget()

    assert fake.calls == 1
    assert any(
        message.get("content", "").startswith("[历史摘要]")
        for message in agent.memory
    )
