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
    _finished: bool = field(default=False, init=False, repr=False)

    def __post_init__(self):
        self._iterator = iter(self.stream)

    def next_event(self) -> Optional[dict[str, Any]]:
        if self._finished:
            return None
        try:
            chunk = next(self._iterator)
        except StopIteration:
            self._finished = True
            return None

        event = None
        if chunk.thinking and chunk.thinking.strip():
            self.thinking += chunk.thinking
            event = {"type": "thinking", "text": chunk.thinking.rstrip()}
        elif chunk.tool_calls:
            self.tool_calls.extend(chunk.tool_calls)
            event = {"type": "tool_calls", "calls": list(chunk.tool_calls)}
        elif chunk.content and chunk.content.strip():
            self.content += chunk.content
            event = {"type": "content", "text": chunk.content.rstrip()}

        if chunk.done:
            self._finished = True
        if event is None and not self._finished:
            return self.next_event()
        return event


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
        out = output_response(agent.send_message(user_input))
        tool_calls = render_response(out)
        while tool_calls:
            results = agent.execute_tool_calls(tool_calls)
            for result in results:
                print(f"工具结果：{result['content']}")
            out = output_response(agent.continue_with_tools(tool_calls, results))
            tool_calls = render_response(out)
        if out.content:
            agent.memory.append({"role": "assistant", "content": out.content})
                
