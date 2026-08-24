"""命令行交互循环。"""

from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from .core.agent import Agent
from .providers import ChatChunk

EXIT_COMMANDS = {"exit", "quit", "q", "退出"}


@dataclass
class Response:
    """流式输出的惰性收集器，渲染时逐块消费并收集。"""

    stream: Iterator[ChatChunk]
    thinking: str = ""
    content: str = ""
    tool_calls: list[Any] = field(default_factory=list)
    _iterator: Iterator[ChatChunk] = field(init=False, repr=False)

    def __post_init__(self):
        self._iterator = iter(self.stream)

    def next_chunk(self) -> Optional[ChatChunk]:
        try:
            chunk = next(self._iterator)
        except StopIteration:
            return None
        if chunk.thinking and chunk.thinking.strip():
            self.thinking += chunk.thinking
        if chunk.tool_calls:
            self.tool_calls.extend(chunk.tool_calls)
        if chunk.content and chunk.content.strip():
            self.content += chunk.content
        return chunk


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
        chunk = out.next_chunk()
        if chunk is None:
            break
        if chunk.thinking and chunk.thinking.strip():
            state = switch_state(state, "thinking", "思考：")
            print(chunk.thinking.rstrip(), end="", flush=True)
        if chunk.tool_calls:  # 真值判断，空列表跳过
            state = switch_state(state, "tool_calling", "工具调用：")
            print(chunk.tool_calls, end="", flush=True)
        if chunk.content and chunk.content.strip():
            state = switch_state(state, "ans", "回答：")
            print(chunk.content.rstrip(), end="", flush=True)
    print()
    return out.tool_calls


def run(agent: Agent) -> None:
    while True:
        user_input = input("user：").strip()
        if not user_input:
            continue
        if user_input.lower() in EXIT_COMMANDS:
            break
        out = output_response(agent.send_message(user_input))
        tool_calls = render_response(out)
        if tool_calls:
            for result in agent.execute_tool_calls(tool_calls):
                print(f"工具结果：{result['content']}")
