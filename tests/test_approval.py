"""审批门契约。"""

import pytest

from yuki.core.agent import Agent
from yuki.skills import ToolRegistry
from yuki.skills.types import Tool

from tests.fake_provider import FakeProvider


def _registry(tmp_path):
    module_dir = tmp_path / "tools"
    module_dir.mkdir(exist_ok=True)
    (module_dir / "danger.py").write_text(
        "def run():\n    return 'ok'\n",
        encoding="utf-8",
    )
    registry = ToolRegistry(None)
    registry.register_tool(
        Tool(
            name="danger",
            description="危险工具",
            parameters={"type": "object", "properties": {}},
            requires_approval=True,
            entry={
                "type": "python",
                "module": "danger.py",
                "handler": "run",
            },
            package="test",
            package_dir=str(module_dir),
        )
    )
    return registry


@pytest.mark.asyncio
async def test_approve_once_not_remembered(settings, tmp_path):
    calls = {"count": 0}

    async def approver(_name, _arguments):
        calls["count"] += 1
        return "y"

    agent = Agent(
        "fake",
        _registry(tmp_path),
        settings,
        provider=FakeProvider(settings=settings),
        approver=approver,
    )
    results = await agent.execute_tool_calls(
        [{"function": {"name": "danger", "arguments": {}}}]
    )
    assert results[0]["content"] == "ok"
    assert not agent.session.is_approved("danger")
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_approve_remember_session(settings, tmp_path):
    calls = {"count": 0}

    async def approver(_name, _arguments):
        calls["count"] += 1
        return "ya"

    agent = Agent(
        "fake",
        _registry(tmp_path),
        settings,
        provider=FakeProvider(settings=settings),
        approver=approver,
    )
    first = await agent.execute_tool_calls(
        [{"function": {"name": "danger", "arguments": {}}}]
    )
    second = await agent.execute_tool_calls(
        [{"function": {"name": "danger", "arguments": {}}}]
    )
    assert first[0]["content"] == "ok"
    assert second[0]["content"] == "ok"
    assert calls["count"] == 1
    assert agent.session.is_approved("danger")


@pytest.mark.asyncio
async def test_approve_denied(settings, tmp_path):
    async def approver(_name, _arguments):
        return "n"

    agent = Agent(
        "fake",
        _registry(tmp_path),
        settings,
        provider=FakeProvider(settings=settings),
        approver=approver,
    )
    results = await agent.execute_tool_calls(
        [{"function": {"name": "danger", "arguments": {}}}]
    )
    assert results[0]["content"] == "用户拒绝执行"
