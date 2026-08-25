"""无头流式收集与内容清洗。"""

import re
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from ..providers import ChatChunk

THINK_TAGS = ("<think>", "</think>")
SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?])")


def clean_content(text: str, pending: str) -> tuple[str, str, bool]:
    """去掉内容流里的 think 标签，返回清理文本、待续标签、是否出现过标签。"""
    combined = pending + text
    saw_tag = any(tag in combined for tag in THINK_TAGS)
    for tag in THINK_TAGS:
        combined = combined.replace(tag, "")
    for tag in THINK_TAGS:
        for size in range(len(tag) - 1, 0, -1):
            if combined.endswith(tag[:size]):
                return combined[:-size], combined[-size:], saw_tag
    return combined, "", saw_tag


def split_sentences(text: str) -> list[str]:
    return [part for part in SENTENCE_SPLIT.split(text) if part]


@dataclass
class Collected:
    thinking: str = ""
    content: str = ""
    tool_calls: list[Any] = field(default_factory=list)


async def collect_stream(stream: AsyncIterator[ChatChunk]) -> Collected:
    """无头消费流式输出，只清理 think 标签，不做渲染。"""
    result = Collected()
    pending = ""
    buffer = ""
    async for chunk in stream:
        if chunk.thinking:
            result.thinking += chunk.thinking
        if chunk.tool_calls:
            result.tool_calls.extend(chunk.tool_calls)
        if chunk.content is not None:
            clean, pending, _ = clean_content(chunk.content, pending)
            buffer += clean
    result.content = buffer
    return result
