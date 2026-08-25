"""智谱 API 联调测试模版，直接运行即可发送一条测试消息。"""

import asyncio
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(cast(str, __file__)).resolve().parent.parent / "src"))

from yuki_kernel import Agent, Settings, ToolRegistry
from yuki.cli import output_response, render_response


async def main():
    settings = Settings.load()
    agent = Agent(
        settings.model,
        ToolRegistry(),
        settings,
        provider="api",
    )
    response = output_response(agent.send_message("你好，请用一句话介绍你自己。"))
    await render_response(response)
    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
