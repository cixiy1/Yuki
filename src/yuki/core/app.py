"""应用容器：组装 settings / registry / agent，支持热加载。"""

from typing import Optional

from ..config import Settings
from ..skills import ToolRegistry
from ..skills.package_manager import PackageManager
from .agent import Agent, Approver
from .session import Session, SessionStore


class App:
    def __init__(
        self,
        settings: Settings,
        store: SessionStore,
        package_manager: PackageManager,
        approver: Optional[Approver] = None,
    ):
        self.settings = settings
        self.store = store
        self.package_manager = package_manager
        self.approver = approver
        self.session: Session = store.create()
        self.registry = self._build_registry()
        self.agent = self._build_agent()

    def _build_registry(self) -> ToolRegistry:
        return ToolRegistry(
            self.settings.packages_dir,
            available=self.settings.packages or None,
            preload=self.settings.packages_preload,
        )

    def _build_agent(self) -> Agent:
        return Agent(
            self.settings.model,
            self.registry,
            self.settings,
            session=self.session,
            provider=self.settings.provider,
            approver=self.approver,
        )

    async def reload(self) -> None:
        self.settings = Settings.load()
        self.registry = self._build_registry()
        self.agent = self._build_agent()
