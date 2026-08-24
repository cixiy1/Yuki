import os

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

PACKAGES_DIR = os.getenv("PACKAGES_DIR", "packages")
