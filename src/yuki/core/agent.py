from typing import Any, Iterator, Optional

from ..providers import ChatChunk, create_provider
from ..skills import Skills


class Agent:
    def __init__(
        self,
        model: str,
        skill: Skills,
        provider: str = "ollama",
        memory: Optional[list[dict[str, Any]]] = None,
        **provider_kwargs,
    ):
        self.model = model
        self.skill = skill
        self.memory: list[dict[str, Any]] = memory or []
        self.provider = create_provider(provider, model, **provider_kwargs)

    def start(self):
        return self.provider.start()

    def close(self, skip_unload: bool = False):
        return self.provider.close(skip_unload=skip_unload)

    def send_message(self, user_message: str) -> Iterator[ChatChunk]:
        messages = self.memory + [{"role": "user", "content": user_message}]
        return self.provider.chat(messages, tools=self.skill.tools)
