import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "ollama")

AGENT_MODEL = os.getenv("AGENT_MODEL", "qwen3:8b")
AGENT_THINK = os.getenv("AGENT_THINK", "true").lower() in {"1", "true", "yes"}
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_packages_dir = Path(os.getenv("PACKAGES_DIR", "packages"))
PACKAGES_DIR = str(_packages_dir if _packages_dir.is_absolute() else PROJECT_ROOT / _packages_dir)
