"""审批门：判断工具是否需要审批并调用外部审批器。"""

from typing import Any, Awaitable, Callable, Optional

from ...skills import ToolRegistry

Approver = Callable[[str, dict[str, Any]], Awaitable[str]]
SessionProvider = Callable[[], Any]
ApproverProvider = Callable[[], Optional[Approver]]


class ApprovalGate:
    def __init__(
        self,
        registry: ToolRegistry,
        session_provider: SessionProvider,
        approver_provider: ApproverProvider,
    ):
        self.registry = registry
        self.session_provider = session_provider
        self._approver_provider = approver_provider

    async def check(
        self,
        name: str,
        arguments: Optional[dict[str, Any]] = None,
    ) -> bool:
        if not self.registry.needs_approval(name):
            return True
        session = self.session_provider()
        if session.is_approved(name):
            return True
        approver = self._approver_provider()
        if approver is None:
            return False
        answer = (await approver(name, arguments or {})).strip()
        if answer == "ya":
            session.approve(name)
            return True
        if answer.startswith("y"):
            rest = answer[1:].strip()
            if rest.isdigit():
                session.approve(name, int(rest))
            return True
        return False
