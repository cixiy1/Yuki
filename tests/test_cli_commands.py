"""CLI 斜杠命令契约。"""

import pytest

from yuki.commands import handle_command
from yuki_kernel.core.app import App
from yuki_kernel.providers import ChatChunk
from yuki_kernel.skills.package_manager import PackageManager

from tests.fake_provider import FakeProvider


@pytest.mark.asyncio
async def test_session_commands(settings, store, tmp_path):
    app = App(
        settings,
        store,
        PackageManager(tmp_path / "packages"),
    )
    app.agent.provider = FakeProvider(
        script=[[ChatChunk(content="ok"), ChatChunk(done=True)]],
        settings=settings,
    )
    app.session.messages.append({"role": "user", "content": "你好"})

    await handle_command(app, "/save 测试会话")
    assert [meta.name for meta in store.list_sessions()] == ["测试会话"]

    await handle_command(app, "/new")
    assert [message["role"] for message in app.agent.memory] == ["system"]

    await handle_command(app, "/load 测试会话")
    assert app.agent.session.name == "测试会话"
    assert app.agent.memory[-1] == {"role": "user", "content": "你好"}
    assert app.session is app.agent.session

    await handle_command(app, "/sessions")
    assert [meta.name for meta in store.list_sessions()] == ["测试会话"]
