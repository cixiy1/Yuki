# Yuki

一个小型 Agent 示例：通过 provider 抽象同时支持本地 Ollama 和 OpenAI 兼容 API。

## 运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 默认使用本地 Ollama
yuki

# 使用 OpenAI 兼容 API
AGENT_PROVIDER=api 
AGENT_MODEL=你的模型名 \
OPENAI_API_KEY=你的密钥 
OPENAI_BASE_URL=https://api.openai.com/v1 \
yuki
```

未安装时可直接用源码运行：`PYTHONPATH=src python -m yuki`。

`AGENT_PROVIDER` 可选 `ollama`、`api`；`AGENT_MODEL` 默认 `qwen3:8b`。

## 结构

```text
src/
  yuki/                    # 主包
    __main__.py            # 入口
    config.py              # 环境变量配置
    core/agent.py          # Agent
    providers/             # Provider 抽象与实现
      base.py              # Provider / ChatChunk
      ollama.py            # Ollama 本地服务与 provider
      api.py               # OpenAI 兼容 API provider
    skills/                # 工具注册与实现
      registry.py
docs/                      # 开发参考资料
pyproject.toml
```
