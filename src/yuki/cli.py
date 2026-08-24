"""命令行交互循环。"""
from typing import Iterator

from .core.agent import Agent
from .providers import ChatChunk

EXIT_COMMANDS = {"exit", "quit", "q", "退出"}


def run(agent: Agent) -> None:
    while True:
        user_input = input("user：").strip()
        if not user_input:
            continue
        if user_input.lower() in EXIT_COMMANDS:
            break
        output_response(agent.send_message(user_input))


def output_response(stream: Iterator[ChatChunk]) -> None:
    state = "initial"  # initial | thinking | tool_calling | ans

    def switch_state(current_state, next_state, label):
        if current_state != next_state:
            if current_state != "initial":
                print()  # 段落间换行
            print(label, end="")
        return next_state

    for chunk in stream:
        if chunk.done:
            continue
        if chunk.thinking and chunk.thinking.strip():
            state = switch_state(state, "thinking", "思考：")
            print(chunk.thinking.rstrip(), end="", flush=True)
        elif chunk.tool_calls:  # 真值判断，空列表跳过
            state = switch_state(state, "tool_calling", "工具调用：")
            print(chunk.tool_calls, end="", flush=True)
        elif chunk.content is not None:
            state = switch_state(state, "ans", "回答：")
            print(chunk.content, end="", flush=True)
    print()
