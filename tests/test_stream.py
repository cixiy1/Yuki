"""流式事件与 think 去重契约。"""

import pytest

from yuki.cli import output_response
from yuki_kernel.providers import ChatChunk


@pytest.mark.asyncio
async def test_stream_events_and_dedup():
    async def stream():
        yield ChatChunk(thinking="思考中")
        yield ChatChunk(content="纽约气温22°C。</think>纽约气温22°C。")
        yield ChatChunk(done=True)
        yield ChatChunk(content="多余内容")

    out = output_response(stream())
    events = []
    while True:
        event = await out.next_event()
        if event is None:
            break
        events.append(event)

    assert events[0]["type"] == "thinking"
    assert out.content == "纽约气温22°C。"
    assert await out.next_event() is None
