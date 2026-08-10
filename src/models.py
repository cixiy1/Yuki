import ollama
import skills
import core.ollama_service

# 提前实例化工具类
skills.Skills()


class Agent:
    def __init__(self, model, skill, memory=None):
        if memory is None:
            memory = []
        self.model = model
        self.memory = memory
        self.skill = skill

    @staticmethod
    def start():
        return core.ollama_service.start_ollama_service()

    def close(self):
        # 回收模型
        try:
            ollama.generate(model=self.model, prompt="", keep_alive="0s")
            print("模型已回收")
        except Exception as e:
            print("模型回收失败：", e)
        # 结束ollama进程
        return core.ollama_service.stop_ollama_service()

    def send_message(self, user_message):
        user_message = {"role": "user", "content": user_message}

        stream = ollama.chat(
            model=self.model,
            messages=self.memory + [user_message],
            tools=self.skill.tools,
            stream=True,
            think=True
        )
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

        thinking = ""  # 累积，供后续使用
        content = ""
        tool_calls = []

        for chunk in stream:
            if chunk.done:
                continue
            msg = chunk.message
            if msg.thinking is not None:
                state = switch_state(state, "thinking", "思考：")
                thinking += msg.thinking
                print(msg.thinking, end="", flush=True)
            elif msg.tool_calls:  # 真值判断，空列表跳过
                state = switch_state(state, "tool_calling", "工具调用：")
                tool_calls.extend(msg.tool_calls)
                print(msg.tool_calls, end="", flush=True)
            elif msg.content is not None:
                state = switch_state(state, "ans", "回答：")
                content += msg.content
                print(msg.content, end="", flush=True)
        print()

        return True
