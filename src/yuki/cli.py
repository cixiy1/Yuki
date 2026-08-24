"""命令行交互循环。"""

from dataclasses import dataclass, field
from typing import Any, Iterator

from .core.agent import Agent
from .providers import ChatChunk

EXIT_COMMANDS = {"exit", "quit", "q", "退出"}


@dataclass
class Response:
    """流式输出的收集器，迭代时才真正消费底层流。"""

    stream: Iterator[ChatChunk]
    thinking: str = ""
    content: str = ""
    tool_calls: list[Any] = field(default_factory=list)

    def __iter__(self):
        for chunk in self.stream:
            if chunk.thinking and chunk.thinking.strip():
                self.thinking += chunk.thinking
            if chunk.tool_calls:
                self.tool_calls.extend(chunk.tool_calls)
            if chunk.content and chunk.content.strip():
                self.content += chunk.content
            yield chunk
            if chunk.done:
                break


def output_response(stream: Iterator[ChatChunk]) -> Response:
    """拿输出：把模型流包装成可收集的 Response。"""

    return Response(stream)


def render_response(response: Response) -> list[Any]:
    """渲染：消费 Response 并打印思考/工具调用/回答，返回工具调用。"""

    state = "initial"  # initial | thinking | tool_calling | ans

    def switch_state(current_state, next_state, label):
        if current_state != next_state:
            if current_state != "initial":
                print()  # 段落间换行
            print(label, end="")
        return next_state

    for chunk in response:
        if chunk.thinking and chunk.thinking.strip():
            state = switch_state(state, "thinking", "思考：")
            print(chunk.thinking.rstrip(), end="", flush=True)
        if chunk.tool_calls:  # 真值判断，空列表跳过
            state = switch_state(state, "tool_calling", "工具调用：")
            print(chunk.tool_calls, end="", flush=True)
        if chunk.content and chunk.content.strip():
            state = switch_state(state, "ans", "回答：")
            print(chunk.content.rstrip(), end="", flush=True)
        if chunk.done:
            break
    print()
    return response.tool_calls


def run(agent: Agent) -> None:
    while True:
        user_input = input("user：").strip()
        if not user_input:
            continue
        if user_input.lower() in EXIT_COMMANDS:
            break
        response = output_response(agent.send_message(user_input))
        tool_calls = render_response(response)
        if tool_calls:
            for result in agent.execute_tool_calls(tool_calls):
                print(f"工具结果：{result['content']}")
