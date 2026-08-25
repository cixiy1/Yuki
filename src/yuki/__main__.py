"""Yuki 入口。"""

import asyncio
import os
import sys
import traceback
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(cast(str, __file__)).resolve().parent.parent))

from yuki.cli import cli_approver, run
from yuki_kernel.config import Settings
from yuki_kernel.core.app import App
from yuki_kernel.core.session import SessionStore
from yuki_kernel.skills.package_manager import PackageManager


def _env_mtime(project_root: Path):
    env_file = project_root / ".env"
    if not env_file.exists():
        return None
    return env_file.stat().st_mtime


async def watch_env(app: App, stop: asyncio.Event):
    last = _env_mtime(app.settings.project_root)
    while not stop.is_set():
        await asyncio.sleep(2)
        current = _env_mtime(app.settings.project_root)
        if current is not None and current != last:
            last = current
            await app.reload()
            print("检测到 .env 变化，配置已热加载")


async def main():
    settings = Settings.load()
    store = SessionStore(settings.data_dir)
    package_manager = PackageManager(settings.packages_dir)
    app = App(settings, store, package_manager, approver=cli_approver)
    stop = asyncio.Event()
    watcher = asyncio.create_task(watch_env(app, stop))

    try:
        await app.agent.start()
        await run(app)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print(".\n手动退出....")
    finally:
        stop.set()
        watcher.cancel()
        try:
            await watcher
        except asyncio.CancelledError:
            pass
        err = sys.exc_info()[1]
        if err is not None:
            traceback.print_exception(*sys.exc_info())
        try:
            await app.agent.close()
            print("\n程序结束，资源清理完成")
        except Exception as err:
            print(f"资源清理异常：{repr(err)}")
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1 if err is not None else 0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
