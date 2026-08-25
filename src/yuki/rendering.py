"""Yuki 外壳的渲染清洗：去重与整句拆分只属于 UI 层。"""

import re

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
