import json
from typing import Any, Iterator, Mapping, Optional, Sequence, cast

from ..config import AGENT_THINK, OPENAI_API_KEY, OPENAI_BASE_URL
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
        if AGENT_THINK:
            extra_body = kwargs.setdefault("extra_body", {})
            extra_body.setdefault("thinking", {"type": "enabled"})
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=cast(Any, messages),
            tools=cast(Any, tools),
            stream=True,
            **kwargs,
        )
        for chunk in stream:
            chunk = cast(Any, chunk)
            choices = chunk.choices or []
            if not choices:
                continue
            choice = choices[0]
            delta = getattr(choice, "delta", None)
            if delta is None:
                continue
            thinking = getattr(delta, "reasoning_content", None) or getattr(delta, "thinking", None)
            yield ChatChunk(
                thinking=thinking,
                content=getattr(delta, "content", None),
                tool_calls=list(getattr(delta, "tool_calls", None) or []),
                done=bool(getattr(choice, "finish_reason", False)),
            )

    def close(self, skip_unload: bool = False):
        self.client.close()

    def build_tool_messages(
        self,
        tool_calls: list[dict[str, Any]],
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        assistant = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": call.get("id") or f"call_{index}",
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": json.dumps(call["arguments"], ensure_ascii=False),
                    },
                }
                for index, call in enumerate(tool_calls)
            ],
        }
        tool_messages = [
            {
                "role": "tool",
                "tool_call_id": call.get("id") or f"call_{index}",
                "content": result["content"],
            }
            for index, (call, result) in enumerate(zip(tool_calls, results))
        ]
        return [assistant] + tool_messages
