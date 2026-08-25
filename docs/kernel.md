# yuki_kernel 使用指南

`yuki_kernel` 是一个可嵌入的 agent 内核，定位是“空白大脑”：它不携带身份、人格或具体业务逻辑，
只提供推理、工具、记忆和生命周期能力。外部软件负责注入“我是谁”、会话记忆、长期记忆和工具，
并决定自己的架构（例如思考层、注意力层、动作层）。

## 安装与导入

```bash
pip install -e .
```

```text
from yuki_kernel import Agent, Settings, ToolRegistry
```

未安装时用源码运行：`PYTHONPATH=src python -m yuki` 或让外部程序把 `src` 加入 `sys.path`。

## 最小示例：无头聊天

```text
import asyncio

from yuki_kernel import Agent, Settings, ToolRegistry


async def main():
    agent = Agent(
        "qwen3:8b",
        ToolRegistry(),
        Settings(provider="my_provider", model="qwen3:8b"),
        provider=MyProvider(model, settings),   # 直接传入 Provider 实例
    )
    result = await agent.turn("你好")
    print(result.content)


asyncio.run(main())
```

`Agent.turn()` 是一个完整回合：追加用户消息、跑模型、执行工具闭环、还原工具包、
写入长期记忆，最后返回 `TurnResult`。

## 接入 Provider

内核只定义 `ChatChunk` 和 `Provider` 抽象，不内置任何具体模型厂商。
外部软件实现自己的 Provider，注册名字或直接传入实例：

```text
from yuki_kernel import Provider
from yuki_kernel.providers import register_provider

class MyProvider(Provider):
    async def chat(self, messages, tools=None, **kwargs):
        ...

register_provider("my_provider", MyProvider)
settings = Settings(provider="my_provider", model="my-model")
```

也可以不注册，直接把 Provider 实例传给 Agent。Yuki 示例在 `src/yuki/providers.py`
注册了 `ollama` 和 `api` 两个实现，仅作为参考。

## 注入人格（后天记忆）

内核本身没有身份，也不会自动加载任何人格。使用内核的人负责配置。

方式一：直接给 Agent 传 `system_prompt`：

```text
agent = Agent(
    "glm-4.5-air",
    registry,
    settings,
    system_prompt="你是 Yuki，一个本地运行的 AI 助手。",
)
```

方式二：用环境变量预加载人格包：

```text
AGENT_PACKAGES_PRELOAD=yuki_persona
```

方式三：在代码里配置预加载：

```text
settings = Settings(provider="ollama", model="qwen3:8b")
settings.packages_preload = ["yuki_persona"]

agent = Agent(model, ToolRegistry(settings.packages_dir, preload=settings.packages_preload), settings)
```

仓库提供示例人格包 `packages/yuki_persona`，是否加载、加载什么人格，完全由外层软件决定。

## 会话记忆：换记忆

会话是 `Session`，消息是 OpenAI 风格 messages 列表。JSONL 就是记忆文件：

```text
from pathlib import Path

from yuki_kernel import SessionStore

# 导出记忆
SessionStore.export(session, Path("robot.jsonl"))

# 导入记忆，生成一个新 Session
loaded = SessionStore.import_file(Path("robot.jsonl"), name="robot")

# 给 Agent 换记忆
agent.switch_session(loaded)
```

`SessionStore` 需要外部软件传入 `data_dir`，内核不假设任何目录；
`save/load/list_sessions` 负责在外部给定的目录里持久化和索引。

## 长期记忆

长期记忆按 `namespace` 隔离，适合多个机器人共用同一个内核；存储目录由外部软件传入：

```text
from yuki_kernel import MemoryStore

memory = MemoryStore(Path("data"), namespace="robot_a")
memory.add(session_id, "用户：你好\n助手：你好呀")
hits = memory.search("你好")
```

模型侧通过 `search_memory` 工具按需检索，不自动注入。`App` 会自动把
`MemoryStore.search_text` 接到 `search_memory` 上。

## 工具与外置包

```text
from yuki_kernel import ToolRegistry

registry = ToolRegistry(
    packages_dir,                # 外部软件提供包目录
    available=["weather"],          # 白名单，留空表示全部
    preload=["weather"],            # 启动即加载
)
```

注册表自带元工具：

- `list_packages`：查看可用包
- `load_package` / `unload_package`：按需加载/卸载
- `search_memory`：检索长期记忆

外置包格式见 [docs/tools/manifest.md](tools/manifest.md)。

## 流式调用（自定义渲染）

推荐用 `turn_stream()`，工具闭环、包还原、记忆写入都在内核内完成：

```text
async for event in agent.turn_stream("你好"):
    if event.kind == "content":
        print(event.text, end="", flush=True)
```

事件类型：`thinking / content / tool_calls / tool_result / package_restored / done`。
内核只产生原始事件，不做清洗、去重或渲染；`content` / `thinking` 可能是原始文本
（含 think 标签），由外壳自己处理。示例外壳的清洗逻辑在 `src/yuki/rendering.py`。

需要最底层的裸流时，也可以直接消费 provider 流：

```text
async for chunk in agent.send_message("你好"):
    print(chunk.content, end="", flush=True)
```

`agent.turn()` 等价于收集 `turn_stream()` 的全部事件，无头场景直接用。

## 中间件与事件

```text
from yuki_kernel.core.bus import EventBus
from yuki_kernel.core.middleware import Middleware

class LogMiddleware(Middleware):
    async def before(self, event):
        print("before", event.kind)
        return event

bus = EventBus()
bus.subscribe("assistant_chunk", lambda event: print("chunk"))

agent = Agent(..., middlewares=[LogMiddleware()], bus=bus)
```

事件类型：`user_message / before_model / assistant_chunk / tool_call /
tool_result / session_start / session_end / package_load / package_unload /
config_reload`。

## 配置

内核不读取环境变量，也不依赖 `.env` 或项目目录。`Settings` 是完全由外部软件构造的参数对象：

```text
settings = Settings(
    provider="api",
    model="glm-4.5-air",
    packages_dir=Path("/your/project/packages"),
    data_dir=Path("/your/project/data"),
    retry_max=3,
)
```

字段说明：

- `provider` / `model`：模型提供方和模型名
- `think`：是否开启思考
- `openai_base_url` / `openai_api_key`：API provider
- `ollama_host` / `ollama_port`：Ollama 地址
- `packages_dir` / `packages` / `packages_preload`：外置包目录与加载策略
- `max_context_tokens` / `keep_recent_messages`：上下文预算
- `memory_limit` / `namespace`：长期记忆
- `retry_max` / `retry_base`：重试
- `data_dir`：会话与长期记忆目录

`packages_dir`、`data_dir` 传 `None` 时内核不加载外置包、不启用持久化记忆。
Yuki 示例自己的 `load_settings()` 负责读环境变量并填充这些字段，那属于外壳层。

完整说明见 [.env.example](../.env.example)。

## 示例 agent：Yuki

仓库里的 `src/yuki/` 是基于内核实现的聊天外壳，作为外部软件的参考实现：

```bash
PYTHONPATH=src .venv/bin/python -m yuki
```

它默认也是空白大脑；要让 Yuki 回答“我是 Yuki”，先配置
`AGENT_PACKAGES_PRELOAD=yuki_persona`，再启动。

斜杠命令：

- `/save <名字>`、`/load <名字>`、`/sessions`、`/new`
- `/reload`
- `/pkg install|remove|list`

## 外部软件架构建议

内核不规定上层结构。一个实体机器人可以这样组合：

- 思考层：把传感器/环境状态转成消息，调 `agent.turn()` 生成决策。
- 注意力层：决定把哪些会话、记忆、工具放入 registry 和 session。
- 动作层：消费 `TurnResult.tool_calls`，执行物理/软件动作。

内核提供完整调用面，上层只负责“给什么记忆、给什么工具、怎么用结果”。
