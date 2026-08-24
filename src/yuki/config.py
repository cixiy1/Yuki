import os

AGENT_MODEL = os.getenv("AGENT_MODEL", "qwen3:8b")
AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "ollama")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
