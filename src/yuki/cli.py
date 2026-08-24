"""命令行交互循环。"""

from dataclasses import dataclass, field
from typing import Any, Iterator

from .core.agent import Agent
from .providers import ChatChunk

EXIT_COMMANDS = {"exit", "quit", "q", "退出"}


@dataclass
class Response:
    """收集到的模型输出，按出现顺序保存。"""

    events: list[tuple[str, Any]] = field(default_factory=list)

    @property
    def tool_calls(self) -> list[Any]:
        calls = []
        for kind, value in self.events:
            if kind == "tool_calls":
                calls.extend(value)
        return calls


def output_response(stream: Iterator[ChatChunk]) -> Response:
    """拿输出：消费流并收集思考、工具调用、回答。"""

    response = Response()
    for chunk in stream:
        if chunk.thinking and chunk.thinking.strip():
            response.events.append(("thinking", chunk.thinking.rstrip()))
        if chunk.tool_calls:
            response.events.append(("tool_calls", list(chunk.tool_calls)))
        if chunk.content and chunk.content.strip():
            response.events.append(("content", chunk.content.rstrip()))
        if chunk.done:
            break
    return response


def render_response(response: Response) -> None:
    """渲染：把收集好的 Response 输出到终端。"""

    state = "initial"  # initial | thinking | tool_calling | ans

    def switch_state(current_state, next_state, label):
        if current_state != next_state:
            if current_state != "initial":
                print()  # 段落间换行
            print(label, end="")
        return next_state

    for kind, value in response.events:
        if kind == "thinking":
            state = switch_state(state, "thinking", "思考：")
            print(value, end="", flush=True)
        elif kind == "tool_calls":
            state = switch_state(state, "tool_calling", "工具调用：")
            print(value, end="", flush=True)
        elif kind == "content":
            state = switch_state(state, "ans", "回答：")
            print(value, end="", flush=True)
    print()


def run(agent: Agent) -> None:
    while True:
        user_input = input("user：").strip()
        if not user_input:
            continue
        if user_input.lower() in EXIT_COMMANDS:
            break
        out = output_response(agent.send_message(user_input))
        render_response(out)
        if out.tool_calls:
            for result in agent.execute_tool_calls(out.tool_calls):
                print(f"工具结果：{result['content']}")
