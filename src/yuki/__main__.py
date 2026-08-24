import atexit
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(cast(str, __file__)).resolve().parent.parent))

from yuki.config import AGENT_MODEL, AGENT_PROVIDER
from yuki.core.agent import Agent
from yuki.skills import Skills
from yuki.cli import run


def safe_clean(agent, skip_unload: bool = False):
    try:
        agent.close(skip_unload=skip_unload)
        print("程序结束，资源清理完成")
    except Exception as err:
        print(f"资源清理异常：{repr(err)}")


def main():
    skills = Skills()
    agent = Agent(AGENT_MODEL, skills, provider=AGENT_PROVIDER)
    atexit.register(safe_clean, agent)

    try:
        agent.start()
        run(agent)
    except KeyboardInterrupt:
        print(".\n手动退出....")
        safe_clean(agent, skip_unload=True)
        atexit.unregister(safe_clean)


if __name__ == '__main__':
    main()
