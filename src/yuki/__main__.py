import atexit

from .config import AGENT_MODEL, AGENT_PROVIDER
from .core.agent import Agent
from .skills import Skills


def safe_clean(agent, skip_unload: bool = False):
    try:
        agent.close(skip_unload=skip_unload)
        print("资源清理完成")
    except Exception as err:
        print(f"资源清理异常：{repr(err)}")


def main():
    skills = Skills()
    agent = Agent(AGENT_MODEL, skills, provider=AGENT_PROVIDER)
    atexit.register(safe_clean, agent)

    try:
        agent.start()
        user_input = input("user：").strip() or "查看一下纽约天气"
        agent.send_message(user_input)
    except KeyboardInterrupt:
        print(".\n正在退出")
        safe_clean(agent, skip_unload=True)
        atexit.unregister(safe_clean)

if __name__ == '__main__':
    main()
