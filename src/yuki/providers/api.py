from typing import Any, Iterator, Mapping, Optional, Sequence, cast

from ..config import OPENAI_API_KEY, OPENAI_BASE_URL
from .base import ChatChunk, Provider


class ApiProvider(Provider):
    """OpenAI 兼容 API 的 provider，密钥和地址可通过环境变量提供"""

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model)
        try:
            from openai import OpenAI
        except ImportError as err:
            raise ImportError("ApiProvider 需要安装 openai，请先执行 pip install openai") from err
        self.client = OpenAI(
            api_key=api_key or OPENAI_API_KEY,
            base_url=base_url or OPENAI_BASE_URL,
        )

    def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        **kwargs,
    ) -> Iterator[ChatChunk]:
        kwargs.pop("stream", None)
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=cast(Any, messages),
            tools=cast(Any, tools),
            stream=True,
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

    def close(self, skip_unload: bool = False):
        self.client.close()
