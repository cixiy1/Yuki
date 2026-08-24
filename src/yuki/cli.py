"""命令行交互循环。"""

import re
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from .core.agent import Agent
from .providers import ChatChunk

EXIT_COMMANDS = {"exit", "quit", "q", "退出"}

THINK_TAGS = ("<think>", "</think>")
SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?])")


def clean_content(text: str, pending: str) -> tuple[str, str]:
    """去掉内容流里的 think 标签，标签可能被切成多块。"""
    combined = pending + text
    for tag in THINK_TAGS:
        combined = combined.replace(tag, "")
    for tag in THINK_TAGS:
        for size in range(len(tag) - 1, 0, -1):
            if combined.endswith(tag[:size]):
                return combined[:-size], combined[-size:]
    return combined, ""


def split_sentences(text: str) -> list[str]:
    return [part for part in SENTENCE_SPLIT.split(text) if part]


@dataclass
class Response:
    """流式输出的惰性收集器，渲染时逐块消费并收集。"""

    stream: Iterator[ChatChunk]
    thinking: str = ""
    content: str = ""
    tool_calls: list[Any] = field(default_factory=list)
    _iterator: Iterator[ChatChunk] = field(init=False, repr=False)
    _finished: bool = field(default=False, init=False, repr=False)
    _content_pending: str = field(default="", init=False, repr=False)
    _content_buffer: str = field(default="", init=False, repr=False)
    _last_sentence: str = field(default="", init=False, repr=False)
    _flush_pending: str = field(default="", init=False, repr=False)

    def __post_init__(self):
        self._iterator = iter(self.stream)

    def next_event(self) -> Optional[dict[str, Any]]:
        if self._finished:
            return self._flush_content()
        try:
            chunk = next(self._iterator)
        except StopIteration:
            self._finished = True
            return self._flush_content()

        event = None
        if chunk.thinking and chunk.thinking.strip():
            self.thinking += chunk.thinking
            event = {"type": "thinking", "text": chunk.thinking.rstrip()}
        elif chunk.tool_calls:
            self.tool_calls.extend(chunk.tool_calls)
            event = {"type": "tool_calls", "calls": list(chunk.tool_calls)}
        elif chunk.content is not None:
            clean, pending = clean_content(chunk.content, self._content_pending)
            self._content_pending = pending
            self._content_buffer += clean
            event = self._emit_content()

        if chunk.done:
            self._finished = True
            if self._content_buffer:
                self._flush_pending = self._content_buffer
                self._content_buffer = ""
        if event is None and not self._finished:
            return self.next_event()
        if event is None:
            return self._flush_content()
        return event

    def _emit_content(self) -> Optional[dict[str, Any]]:
        sentences = split_sentences(self._content_buffer)
        self._content_buffer = ""
        emitted = []
        for sentence in sentences:
            key = sentence.strip()
            if not key or key == self._last_sentence:
                continue
            self._last_sentence = key
            self.content += sentence
            emitted.append(sentence)
        if not emitted:
            return None
        return {"type": "content", "text": "".join(emitted)}

    def _flush_content(self) -> Optional[dict[str, Any]]:
        text = self._flush_pending
        self._flush_pending = ""
        if not text or text.strip() == self._last_sentence:
            return None
        self._last_sentence = text.strip()
        self.content += text
        return {"type": "content", "text": text}


def output_response(stream: Iterator[ChatChunk]) -> Response:
    """拿输出：把模型流包装成边收集边渲染的 Response。"""

    return Response(stream)


def render_response(out: Response) -> list[Any]:
    """渲染：通过 out 逐块取输出，边取边打印，返回工具调用。"""

    state = "initial"  # initial | thinking | tool_calling | ans

    def switch_state(current_state, next_state, label):
        if current_state != next_state:
            if current_state != "initial":
                print()  # 段落间换行
            print(label, end="")
        return next_state

    while True:
        event = out.next_event()
        if event is None:
            break
        if event["type"] == "thinking":
            state = switch_state(state, "thinking", "思考：")
            print(event["text"], end="", flush=True)
        elif event["type"] == "tool_calls":
            state = switch_state(state, "tool_calling", "工具调用：")
            print(event["calls"], end="", flush=True)
        elif event["type"] == "content":
            state = switch_state(state, "ans", "回答：")
            print(event["text"], end="", flush=True)
    print()
    return out.tool_calls


def run(agent: Agent) -> None:
    while True:
        user_input = input("user：").strip()
        if not user_input:
            continue
        if user_input.lower() in EXIT_COMMANDS:
            break
        active_packages = agent.registry.active_packages
        out = output_response(agent.send_message(user_input))
        tool_calls = render_response(out)
        while tool_calls:
            results = agent.execute_tool_calls(tool_calls)
            for result in results:
                print(f"工具结果：{result['content']}")
            out = output_response(agent.continue_with_tools(tool_calls, results))
            tool_calls = render_response(out)
        changed = agent.restore_packages(active_packages)
        if changed:
            print(f"外置包已还原：{'、'.join(changed)}")
        if out.content:
            agent.memory.append({"role": "assistant", "content": out.content})
                
