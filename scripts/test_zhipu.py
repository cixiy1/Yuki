"""智谱 API 联调测试模版，直接运行即可发送一条测试消息。"""

from yuki import Agent, Skills
from yuki.config import AGENT_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL


def main():
    agent = Agent(
        AGENT_MODEL,
        Skills(),
        provider="api",
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
    )
    agent.send_message("你好，请用一句话介绍你自己。")
    agent.close()


if __name__ == "__main__":
    main()
