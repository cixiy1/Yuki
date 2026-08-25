"""Yuki 外壳的渲染清洗：去重与整句拆分只属于 UI 层。"""

import re

from yuki_kernel.core.app import App
from yuki_kernel.core.stream import TagFilter
from yuki_kernel.core.stream import clean_content

SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?])")


def split_sentences(text: str) -> list[str]:
    return [part for part in SENTENCE_SPLIT.split(text) if part]


class ContentFilter:
    """去 think 标签并按整句去重，返回可渲染文本。"""

    def __init__(self):
        self.pending = ""
        self.buffer = ""
        self.last_sentence = ""
        self.saw_think_tag = False

    def feed(self, text: str) -> str:
        clean, pending, saw = clean_content(text, self.pending)
        self.pending = pending
        if saw:
            self.saw_think_tag = True
        self.buffer += clean
        return self._emit()

    def finish(self) -> str:
        return self._emit()

    def _emit(self) -> str:
        sentences = split_sentences(self.buffer)
        self.buffer = ""
        emitted = []
        for sentence in sentences:
            key = sentence.strip()
            if not key:
                continue
            if self.saw_think_tag and key == self.last_sentence:
                continue
            self.last_sentence = key
            emitted.append(sentence)
        return "".join(emitted)


async def render_turn(app: App, line: str) -> None:
    state = "initial"
    content_filter = ContentFilter()
    thinking_filter = TagFilter()

    def switch_state(next_state: str, label: str) -> None:
        nonlocal state
        if state != next_state:
            if state != "initial":
                print()
            print(label, end="")
            state = next_state

    async for event in app.agent.turn_stream(line):
        if event.kind == "thinking":
            text = thinking_filter.feed(event.text)
            if text.strip():
                switch_state("thinking", "思考：")
                print(text, end="", flush=True)
        elif event.kind == "tool_calls":
            switch_state("tool_calling", "工具调用：")
            print(event.calls, end="", flush=True)
        elif event.kind == "content":
            text = content_filter.feed(event.text)
            if text:
                switch_state("ans", "回答：")
                print(text, end="", flush=True)
        elif event.kind == "tool_result":
            print(f"\n工具结果：{event.text}")
            state = "initial"
        elif event.kind == "package_restored":
            print(f"\n外置包已还原：{event.text}")
            state = "initial"
    tail = content_filter.finish()
    if tail:
        switch_state("ans", "回答：")
        print(tail, end="", flush=True)
    print()
