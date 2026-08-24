"""命令行交互循环。"""
from typing import Any, Iterator

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
        tool_calls = render_response(agent.send_message(user_input))
        if tool_calls:
            for result in agent.execute_tool_calls(tool_calls):
                print(f"工具结果：{result['content']}")




def render_response(stream: Iterator[ChatChunk]) -> list[Any]:
    state = "initial"  # initial | thinking | tool_calling | ans
    tool_calls = []

    def switch_state(current_state, next_state, label):
        if current_state != next_state:
            if current_state != "initial":
                print()  # 段落间换行
            print(label, end="")
        return next_state

    for chunk in stream:
        if chunk.thinking and chunk.thinking.strip():
            state = switch_state(state, "thinking", "思考：")
            print(chunk.thinking.rstrip(), end="", flush=True)
        if chunk.tool_calls:  # 真值判断，空列表跳过
            state = switch_state(state, "tool_calling", "工具调用：")
            print(chunk.tool_calls, end="", flush=True)
            tool_calls.extend(chunk.tool_calls)
        if chunk.content and chunk.content.strip():
            state = switch_state(state, "ans", "回答：")
            print(chunk.content.rstrip(), end="", flush=True)
        if chunk.done:
            break
    print()
    return tool_calls
