from .api import ApiProvider
from .base import ChatChunk, Provider
from .ollama import OllamaProvider
from ..config import Settings

__all__ = ["ChatChunk", "Provider", "OllamaProvider", "ApiProvider", "create_provider"]


def create_provider(
    name: str,
    model: str,
    settings: Settings,
) -> Provider:
    providers = {
        "ollama": OllamaProvider,
        "api": ApiProvider,
    }
    try:
        return providers[name](model, settings=settings)
    except KeyError:
        raise ValueError(f"不支持的 provider：{name}，可选 {list(providers)}") from None
