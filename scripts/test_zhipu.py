"""智谱 API 联调测试模版，直接运行即可发送一条测试消息。"""

import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(cast(str, __file__)).resolve().parent.parent / "src"))

from yuki import Agent, ToolRegistry
from yuki.cli import output_response, render_response
from yuki.config import AGENT_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL


def main():
    agent = Agent(
        AGENT_MODEL,
        ToolRegistry(),
        provider="api",
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
    )
    response = output_response(agent.send_message("你好，请用一句话介绍你自己。"))
    render_response(response)
    agent.close()


if __name__ == "__main__":
    main()
