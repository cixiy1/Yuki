"""Yuki 示例聊天外壳：只做渲染和命令，回合编排交给内核 turn_stream。"""

import asyncio
from typing import Any

from yuki_kernel.core.app import App
from yuki_kernel.core.stream import TagFilter
from yuki_kernel.skills.package_manager import LocalDirSource, ZipSource

from .rendering import ContentFilter

EXIT_COMMANDS = {"exit", "quit", "q", "退出"}


async def render_turn(app: App, line: str) -> None:
    state = "initial"
    content_filter = ContentFilter()
    thinking_filter = TagFilter()

    def switch_state(next_state: str, label: str) -> None:
        nonlocal state
        if state != next_state:
            if state != "initial":
                print()
            print(label, end="")
            state = next_state

    async for event in app.agent.turn_stream(line):
        if event.kind == "thinking":
            text = thinking_filter.feed(event.text)
            if text.strip():
                switch_state("thinking", "思考：")
                print(text, end="", flush=True)
        elif event.kind == "tool_calls":
            switch_state("tool_calling", "工具调用：")
            print(event.calls, end="", flush=True)
        elif event.kind == "content":
            text = content_filter.feed(event.text)
            if text:
                switch_state("ans", "回答：")
                print(text, end="", flush=True)
        elif event.kind == "tool_result":
            print(f"\n工具结果：{event.text}")
            state = "initial"
        elif event.kind == "package_restored":
            print(f"\n外置包已还原：{event.text}")
            state = "initial"
    tail = content_filter.finish()
    if tail:
        switch_state("ans", "回答：")
        print(tail, end="", flush=True)
    print()


async def cli_approver(name: str, _arguments: dict[str, Any]) -> str:
    answer = await asyncio.to_thread(
        input,
        f"工具 {name} 需要审批 (y / ya / y <分钟> / n)：",
    )
    return answer.strip()


async def handle_pkg(app: App, arg: str) -> None:
    parts = arg.split(maxsplit=1)
    sub = parts[0] if parts else ""
    ref = parts[1].strip() if len(parts) > 1 else ""

    if sub == "install":
        if not ref:
            print("用法：/pkg install <目录|zip>")
            return
        source = ZipSource() if ref.lower().endswith(".zip") else LocalDirSource()
        try:
            info = await app.package_manager.install(source, ref)
            print(f"已安装：{info.id} {info.version}")
            app.registry.scan_packages(
                app.settings.packages_dir,
                available=app.settings.packages or None,
            )
        except Exception as err:
            print(f"安装失败：{err}")
    elif sub == "remove":
        if not ref:
            print("用法：/pkg remove <id>")
            return
        try:
            app.package_manager.remove(ref)
            print(f"已卸载：{ref}")
            app.registry.scan_packages(
                app.settings.packages_dir,
                available=app.settings.packages or None,
            )
        except Exception as err:
            print(f"卸载失败：{err}")
    elif sub == "list":
        infos = app.package_manager.list_installed()
        if not infos:
            print("暂无已安装包")
            return
        for info in infos:
            print(f"{info.id} {info.version} {info.source}")
    else:
        print("用法：/pkg install <目录|zip> | /pkg remove <id> | /pkg list")


async def handle_command(app: App, line: str) -> bool:
    parts = line.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/save":
        if not arg:
            print("用法：/save <名字>")
            return True
        app.session.name = arg
        await asyncio.to_thread(app.store.save, app.session)
        print(f"会话已保存：{arg}")
    elif cmd == "/load":
        if not arg:
            print("用法：/load <名字>")
            return True
        meta = None
        for item in app.store.list_sessions():
            if item.name == arg:
                meta = item
                break
        if meta is None:
            print(f"找不到会话：{arg}")
            return True
        session = await asyncio.to_thread(app.store.load, meta.session_id)
        if session is None:
            print(f"会话文件缺失：{arg}")
            return True
        app.session = session
        app.agent.switch_session(session)
        print(f"已加载会话：{arg}")
    elif cmd == "/sessions":
        metas = app.store.list_sessions()
        if not metas:
            print("暂无已保存会话")
            return True
        for meta in metas:
            print(f"{meta.name}  {meta.updated_at}")
    elif cmd == "/new":
        app.agent.switch_session(app.store.create())
        print("已开始新会话")
    elif cmd == "/reload":
        await app.reload()
        print("配置已热加载")
    elif cmd == "/pkg":
        await handle_pkg(app, arg)
    else:
        print(f"未知命令：{cmd}")
    return True


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
