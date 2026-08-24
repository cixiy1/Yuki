import os

MODEL = os.getenv("AGENT_MODEL", "qwen3:8b")
PROVIDER = os.getenv("AGENT_PROVIDER", "ollama")
