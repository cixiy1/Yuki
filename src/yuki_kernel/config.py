"""运行配置：集中读取环境变量，支持热加载。"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

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


def _resolve_env_path(name: str) -> Optional[Path]:
    value = os.getenv(name, "")
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else Path.cwd() / path


@dataclass
class Settings:
    """一次加载的完整配置快照。"""

    provider: str = "ollama"
    model: str = "qwen3:8b"
    think: bool = True
    openai_base_url: Optional[str] = None
    openai_api_key: Optional[str] = None
    ollama_host: str = "127.0.0.1"
    ollama_port: int = 11434
    packages_dir: Optional[Path] = None
    packages: list[str] = field(default_factory=list)
    packages_preload: list[str] = field(default_factory=list)
    max_context_tokens: int = 12000
    keep_recent_messages: int = 10
    memory_limit: int = 5
    namespace: str = "default"
    retry_max: int = 3
    retry_base: float = 0.5
    data_dir: Optional[Path] = None

    @classmethod
    def load(cls) -> "Settings":
        if load_dotenv is not None:
            load_dotenv(override=True)
        packages_dir = _resolve_env_path("PACKAGES_DIR")
        data_dir = _resolve_env_path("DATA_DIR")
        return cls(
            provider=os.getenv("AGENT_PROVIDER", "ollama"),
            model=os.getenv("AGENT_MODEL", "qwen3:8b"),
            think=_bool_env("AGENT_THINK", True),
            openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            ollama_host=os.getenv("OLLAMA_HOST", "127.0.0.1"),
            ollama_port=_int_env("OLLAMA_PORT", 11434),
            packages_dir=packages_dir,
            packages=_csv_env("AGENT_PACKAGES"),
            packages_preload=_csv_env("AGENT_PACKAGES_PRELOAD"),
            max_context_tokens=_int_env("AGENT_MAX_CONTEXT_TOKENS", 12000),
            keep_recent_messages=_int_env("AGENT_KEEP_RECENT_MESSAGES", 10),
            memory_limit=_int_env("AGENT_MEMORY_LIMIT", 5),
            namespace=os.getenv("AGENT_NAMESPACE", "default"),
            retry_max=_int_env("AGENT_RETRY_MAX", 3),
            retry_base=_float_env("AGENT_RETRY_BASE", 0.5),
            data_dir=data_dir,
        )
