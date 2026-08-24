from typing import Optional

from .providers import create_provider
from .skills import Skills


class Agent:
    def __init__(self, model: str, skill: Skills, provider: str = "ollama", memory: Optional[list] = None, **provider_kwargs):
        self.model = model
        self.skill = skill
        self.memory = memory or []
        self.provider = create_provider(provider, model, **provider_kwargs)

    def start(self):
        return self.provider.start()

    def close(self):
        return self.provider.close()

    def send_message(self, user_message: str) -> str:
        messages = self.memory + [{"role": "user", "content": user_message}]
        stream = self.provider.chat(messages, tools=self.skill.tools)
        self.output_response(stream)
        return "本次回答结束"

    @staticmethod
    def output_response(stream):
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
            if chunk.thinking is not None:
                state = switch_state(state, "thinking", "思考：")
                print(chunk.thinking, end="", flush=True)
            elif chunk.tool_calls:  # 真值判断，空列表跳过
                state = switch_state(state, "tool_calling", "工具调用：")
                print(chunk.tool_calls, end="", flush=True)
            elif chunk.content is not None:
                state = switch_state(state, "ans", "回答：")
                print(chunk.content, end="", flush=True)
        print()

        return True
