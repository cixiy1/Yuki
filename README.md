# Yuki

全异步 agent 内核：通过 provider 抽象支持 Ollama 和 OpenAI 兼容 API，内置会话持久化、
上下文摘要、中间件/事件、错误重试、审批、本地包管理和契约测试。

工具系统支持内置工具函数、外置工具包和纯提示词包，外置包按需加载，
开发指南见 [docs/tools](docs/tools/README.md)。

内核使用指南见 [docs/kernel.md](docs/kernel.md)。

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

CLI 斜杠命令：

```text
/save <名字> /load <名字> /sessions /new /reload
/pkg install <目录|zip> /pkg remove <id> /pkg list
```

测试：`PYTHONPATH=src .venv/bin/python -m pytest`（dev 依赖：`pytest`、`pytest-asyncio`）。

## 结构

```text
src/
  yuki_kernel/             # 可嵌入的 agent 内核
    config.py              # Settings：环境变量配置与热加载
    core/
      agent.py             # Agent：异步闭环 + 摘要 + 审批 + 钩子
      app.py               # 应用容器与热加载
      session.py           # 会话与 JSONL/SQLite 持久化
      memory.py            # 长期记忆（namespace 隔离）
      stream.py            # 无头流式收集
      events.py            # 事件类型
      middleware.py        # 中间件链
      bus.py               # 事件总线
      errors.py            # 异常与重试判断
    providers/             # Provider 抽象与实现
      base.py              # Provider / ChatChunk
      ollama.py            # Ollama 本地服务与 provider
      api.py               # OpenAI 兼容 API provider
    skills/                # 工具注册与实现
      registry.py          # ToolRegistry：统一内置工具与外置包
      builtin.py           # 内置工具注册表
      builtins/            # 内置工具实现
      external.py          # 外置包发现与校验
      package_manager.py   # 本地包安装/卸载/列表
  yuki/                    # 示例 agent（聊天外壳）
    __main__.py            # 入口与组装
    cli.py                 # 主循环
    commands.py            # 斜杠命令分发
    approver.py            # 审批交互
    rendering.py           # 渲染与清洗
packages/                  # 外置工具包目录
tests/                     # pytest 契约测试
docs/
  tools/                   # 工具系统开发指南
pyproject.toml
```
