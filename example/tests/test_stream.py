"""流式清洗与无头收集契约。"""

# noinspection PyUnresolvedReferences
import pytest

from yuki.rendering import ContentFilter
# noinspection PyUnresolvedReferences
from yuki_kernel.core.context import collect_stream
# noinspection PyUnresolvedReferences
from yuki_kernel.providers import ChatChunk


def test_content_filter_dedup():
    content_filter = ContentFilter()
    out = content_filter.feed("纽约22°C。</think>纽约22°C。")
    assert out == "纽约22°C。"


@pytest.mark.asyncio
async def test_collect_stream():
    async def stream():
        yield ChatChunk(thinking="思考中")
        yield ChatChunk(content="你好")
        yield ChatChunk(done=True)

    collected = await collect_stream(stream())
    assert collected.thinking == "思考中"
    assert collected.content == "你好"
