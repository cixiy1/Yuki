import atexit

from .config import MODEL, PROVIDER
from .core.agent import Agent
from .skills import Skills

SKILLS = Skills()
yuki = Agent(MODEL, SKILLS, provider=PROVIDER)


def main():
    yuki.start()
    user_input = input("user：").strip() or "查看一下纽约天气"
    yuki.send_message(user_input)


def safe_clean(agent):
    try:
        agent.close()
        print("程序正常退出，资源清理执行成功")
    except Exception as err:
        print(f"清理函数执行异常：{repr(err)}")


atexit.register(safe_clean, yuki)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        # safe_clean(yuki)
        print(".\n正在退出")
