"""长期记忆契约。"""

import pytest

from yuki.core.agent import Agent
from yuki.core.memory import MemoryStore
from yuki.providers import ChatChunk
from yuki.skills import ToolRegistry

from tests.fake_provider import FakeProvider


class CaptureProvider(FakeProvider):
    def __init__(self, settings):
        super().__init__(
            script=[[ChatChunk(content="ok"), ChatChunk(done=True)]],
            settings=settings,
        )
        self.seen = []

    async def chat(self, messages, tools=None, **kwargs):
        self.seen.append([dict(message) for message in messages])
        async for chunk in super().chat(messages, tools=tools, **kwargs):
            yield chunk


def test_memory_search(tmp_path):
    store = MemoryStore(tmp_path / "data")
    store.add("s1", "用户：你好\n助手：你好呀")
    store.add("s2", "用户：纽约天气\n助手：纽约22度")

    hits = store.search("纽约", limit=5)
    assert any("纽约" in hit.content for hit in hits)


@pytest.mark.asyncio
async def test_memory_injected_before_model(settings, tmp_path):
    store = MemoryStore(tmp_path / "data")
    store.add("old", "用户：纽约天气\n助手：纽约22度")
    fake = CaptureProvider(settings)
    agent = Agent(
        "fake",
        ToolRegistry(None),
        settings,
        provider=fake,
        memory_store=store,
    )

    async for _ in agent.send_message("纽约天气怎么样"):
        pass

    sent = fake.seen[0]
    assert any(
        message["role"] == "system" and "[长期记忆" in message.get("content", "")
        for message in sent
    )


@pytest.mark.asyncio
async def test_memory_skipped_for_history_question(settings, tmp_path):
    store = MemoryStore(tmp_path / "data")
    store.add("old", "用户：纽约天气\n助手：纽约22度")
    fake = CaptureProvider(settings)
    agent = Agent(
        "fake",
        ToolRegistry(None),
        settings,
        provider=fake,
        memory_store=store,
    )

    async for _ in agent.send_message("我之前都发了哪些信息"):
        pass

    sent = fake.seen[0]
    assert not any(
        "[长期记忆" in message.get("content", "")
        for message in sent
        if message["role"] == "system"
    )


@pytest.mark.asyncio
async def test_remember_stores_turn(settings, tmp_path):
    store = MemoryStore(tmp_path / "data")
    agent = Agent(
        "fake",
        ToolRegistry(None),
        settings,
        provider=FakeProvider(settings=settings),
        memory_store=store,
    )

    await agent.remember("你好", "你好呀")

    assert any("你好呀" in hit.content for hit in store.search("你好", 5))
