"""Provider 抽象、内置厂商与注册口。

内置 Provider 采用懒加载：仅当首次创建对应 Provider 时才 import 厂商 SDK，
裸装 yuki-kernel（不装 openai / anthropic extras）也能 import 内核并使用自定义 Provider。
"""

from typing import Callable

from ..config import Settings
from .base import ChatChunk, Provider

__all__ = [
    "AnthropicProvider",
    "ChatChunk",
    "OpenAIProvider",
    "Provider",
    "register_provider",
    "create_provider",
]

_PROVIDERS: dict[str, Callable[[str, Settings], Provider]] = {}


def _register_builtins() -> None:
    """按需把内置 Provider 加入注册表，缺失对应 SDK 时跳过。"""
    if "openai" not in _PROVIDERS:
        try:
            from .openai import OpenAIProvider as _OpenAIProvider

            _PROVIDERS["openai"] = _OpenAIProvider
        except ImportError:
            pass
    if "anthropic" not in _PROVIDERS:
        try:
            from .anthropic import AnthropicProvider as _AnthropicProvider

            _PROVIDERS["anthropic"] = _AnthropicProvider
        except ImportError:
            pass


def _resolve(name: str) -> Callable[[str, Settings], Provider]:
    """返回真实 Provider 类，未安装对应 SDK 时给出清晰报错。"""
    if name not in _PROVIDERS:
        _register_builtins()
    factory = _PROVIDERS.get(name)
    if factory is None:
        # 已知内置名（openai/anthropic）因 SDK 缺失而未注册 → 提示装 extra
        if name in ("openai", "anthropic"):
            raise ImportError(f"{name} Provider 需要安装对应 SDK：pip install yuki-kernel[{name}]")
        raise ValueError(f"未注册的 provider：{name}，可选 {list(_PROVIDERS)}")
    return factory


def register_provider(name: str, factory: Callable[[str, Settings], Provider]) -> None:
    _PROVIDERS[name] = factory


def create_provider(
    name: str,
    model: str,
    settings: Settings,
) -> Provider:
    return _resolve(name)(model, settings)


def AnthropicProvider(*args, **kwargs):  # type: ignore[no-redef]
    """前向引用：未安装 anthropic extra 时，实例化会给出清晰报错。"""
    return _resolve("anthropic")(*args, **kwargs)


def OpenAIProvider(*args, **kwargs):  # type: ignore[no-redef]
    """前向引用：未安装 openai extra 时，实例化会给出清晰报错。"""
    return _resolve("openai")(*args, **kwargs)


# 模块加载时尝试注册；SDK 已装则把真实类回填到顶层名（isinstance 可用），
# 未装则保留转发函数，实例化时才报清晰错误。import 内核本身不强制拖 SDK。
_register_builtins()
if "openai" in _PROVIDERS:
    OpenAIProvider = _PROVIDERS["openai"]  # type: ignore[assignment]
if "anthropic" in _PROVIDERS:
    AnthropicProvider = _PROVIDERS["anthropic"]  # type: ignore[assignment]
