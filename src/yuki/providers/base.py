"""Provider 抽象与统一流式消息。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Mapping, Optional, Sequence

from ..config import Settings


@dataclass
class ChatChunk:
    """统一的流式消息片段，屏蔽不同 provider 的消息结构差异。"""

    thinking: Optional[str] = None
    content: Optional[str] = None
    tool_calls: list = field(default_factory=list)
    done: bool = False


class Provider(ABC):
    def __init__(self, model: str, settings: Optional[Settings] = None):
        self.model = model
        self.settings = settings or Settings.load()

    @abstractmethod
    def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        **kwargs,
    ) -> AsyncIterator[ChatChunk]:
        """调用模型并返回统一格式的异步流式结果。"""

    @abstractmethod
    def build_tool_messages(
        self,
        tool_calls: list[dict[str, Any]],
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """把工具调用和结果构造成可继续对话的消息。"""

    async def start(self) -> bool:
        return True

    async def close(self, skip_unload: bool = False):
        return None
