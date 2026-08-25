"""Yuki 示例：从环境变量构建内核 Settings。"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from yuki_kernel.config import Settings

EXAMPLE_ROOT = Path(__file__).resolve().parent.parent.parent


def _bool_env(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _csv_env(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [part.strip() for part in value.split(",") if part.strip()]


def _resolve_path(value: str, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else EXAMPLE_ROOT / path


def load_settings() -> Settings:
    if load_dotenv is not None:
        load_dotenv(EXAMPLE_ROOT / ".env", override=True)
    return Settings(
        provider=os.getenv("AGENT_PROVIDER", "ollama"),
        model=os.getenv("AGENT_MODEL", "qwen3:8b"),
        think=_bool_env("AGENT_THINK", True),
        openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        ollama_host=os.getenv("OLLAMA_HOST", "127.0.0.1"),
        ollama_port=_int_env("OLLAMA_PORT", 11434),
        packages_dir=_resolve_path(os.getenv("PACKAGES_DIR", ""), EXAMPLE_ROOT / "packages"),
        packages=_csv_env("AGENT_PACKAGES"),
        packages_preload=_csv_env("AGENT_PACKAGES_PRELOAD"),
        max_context_tokens=_int_env("AGENT_MAX_CONTEXT_TOKENS", 12000),
        keep_recent_messages=_int_env("AGENT_KEEP_RECENT_MESSAGES", 10),
        memory_limit=_int_env("AGENT_MEMORY_LIMIT", 5),
        namespace=os.getenv("AGENT_NAMESPACE", "default"),
        retry_max=_int_env("AGENT_RETRY_MAX", 3),
        retry_base=_float_env("AGENT_RETRY_BASE", 0.5),
        data_dir=_resolve_path(os.getenv("DATA_DIR", ""), EXAMPLE_ROOT / "data"),
    )
