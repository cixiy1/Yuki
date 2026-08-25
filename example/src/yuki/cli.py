"""Yuki 示例聊天外壳：只保留主循环。"""

import asyncio

# noinspection PyUnresolvedReferences
from yuki_kernel.core.app import App

from .commands import handle_command
from .rendering import render_turn

EXIT_COMMANDS = {"exit", "quit", "q", "退出"}


async def run(app: App) -> None:
    while True:
        raw = await asyncio.to_thread(input, "user：")
        line = raw.strip()
        if not line:
            continue
        if line.lower() in EXIT_COMMANDS:
            break
        if line.startswith("/"):
            await handle_command(app, line)
            continue
        await render_turn(app, line)
