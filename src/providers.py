import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Optional

import ollama

from .core import ollama_service


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
    def chat(self, messages: list, tools: Optional[list] = None, **kwargs) -> Iterator[ChatChunk]:
        """调用模型并返回统一格式的流式结果"""

    def start(self) -> bool:
        return True

    def close(self):
        return None


class OllamaProvider(Provider):
    def start(self) -> bool:
        return ollama_service.start_ollama_service()

    def chat(self, messages: list, tools: Optional[list] = None, **kwargs) -> Iterator[ChatChunk]:
        kwargs.setdefault("think", True)
        stream = ollama.chat(
            model=self.model,
            messages=messages,
            tools=tools,
            stream=True,
            **kwargs,
        )
        for chunk in stream:
            msg = chunk.message
            yield ChatChunk(
                thinking=msg.thinking,
                content=msg.content,
                tool_calls=list(msg.tool_calls or []),
                done=chunk.done,
            )

    def close(self):
        try:
            ollama.generate(model=self.model, prompt="", keep_alive="0s")
            print("模型已回收")
        except Exception as err:
            print("模型回收失败：", err)
        return ollama_service.stop_ollama_service()


class ApiProvider(Provider):
    """OpenAI 兼容 API 的 provider，密钥和地址可通过环境变量提供"""

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model)
        try:
            from openai import OpenAI
        except ImportError as err:
            raise ImportError("ApiProvider 需要安装 openai，请先执行 pip install openai") from err
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
        )

    def chat(self, messages: list, tools: Optional[list] = None, **kwargs) -> Iterator[ChatChunk]:
        kwargs.setdefault("stream", True)
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            **kwargs,
        )
        for chunk in stream:
            choice = chunk.choices[0] if chunk.choices else None
            if choice is None:
                continue
            delta = choice.delta
            yield ChatChunk(
                thinking=getattr(delta, "thinking", None),
                content=delta.content,
                tool_calls=list(delta.tool_calls or []),
                done=bool(choice.finish_reason),
            )

    def close(self):
        self.client.close()


def create_provider(name: str, model: str, **kwargs) -> Provider:
    providers = {
        "ollama": OllamaProvider,
        "api": ApiProvider,
    }
    try:
        return providers[name](model, **kwargs)
    except KeyError:
        raise ValueError(f"不支持的 provider：{name}，可选 {list(providers)}") from None
