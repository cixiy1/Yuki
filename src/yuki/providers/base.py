from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator, Mapping, Optional, Sequence


@dataclass
class ChatChunk:
    """统一的流式消息片段，屏蔽不同 provider 的消息结构差异"""
    thinking: Optional[str] = None
    content: Optional[str] = None
    tool_calls: list = field(default_factory=list)
    done: bool = False


class Provider(ABC):
    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        **kwargs,
    ) -> Iterator[ChatChunk]:
        """调用模型并返回统一格式的流式结果"""

    @abstractmethod
    def build_tool_messages(
        self,
        tool_calls: list[dict[str, Any]],
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """把工具调用和结果构造成可继续对话的消息"""

    def start(self) -> bool:
        return True

    def close(self, skip_unload: bool = False):
        return None
