# Yuki

一个小型 Agent 示例：通过 provider 抽象同时支持本地 Ollama 和 OpenAI 兼容 API。

## 运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 默认使用本地 Ollama
python -m yuki

# 使用 OpenAI 兼容 API
AGENT_PROVIDER=api AGENT_MODEL=你的模型名 \
OPENAI_API_KEY=你的密钥 OPENAI_BASE_URL=https://api.openai.com/v1 \
python -m yuki
```

`AGENT_PROVIDER` 可选 `ollama`、`api`；`AGENT_MODEL` 默认 `qwen3:8b`。

## 结构

```text
yuki/                     # 主包
  __main__.py             # 入口
  models.py               # Agent
  providers.py            # Provider 抽象与实现
  skills.py               # 工具定义
  core/ollama_service.py  # Ollama 本地服务
docs/                     # 开发参考资料
requirements.txt
```
