# yuki_kernel 使用指南

## 定位

`yuki_kernel` 是一个可嵌入的 agent 内核，定位是“空白大脑”：

- 不携带身份、人格或具体业务逻辑。
- 不读取环境变量，不依赖 `.env`、`data/`、`packages/` 等外部文件或目录。
- 不内置任何模型厂商。

内核只提供四类能力：

- 推理编排：`Agent.turn()` / `turn_stream()`，包含工具闭环、包还原、记忆写入。
- 记忆：短期会话（`Session`）与长期记忆（`MemoryStore`）。
- 工具：注册表、外置包、审批规则。
- 扩展：`Provider` 抽象、事件、中间件、错误归一。

外部软件负责：实现 Provider、注入人格、决定会话和包目录、渲染 UI、管理进程生命周期。

## 安装与导入

```bash
pip install -e .
```

```text
from yuki_kernel import (
    Agent,
    ChatChunk,
    MemoryStore,
    Provider,
    SessionStore,
    Settings,
    ToolRegistry,
    register_provider,
)
```

不安装时把 `src` 加入 `sys.path`，或直接把 `yuki_kernel/` 复制到自己的项目里。

## 最小可运行示例

```text
import asyncio

from yuki_kernel import Agent, ChatChunk, Provider, Settings, ToolRegistry


class EchoProvider(Provider):
    def build_tool_messages(self, tool_calls, results):
        return []

    async def chat(self, messages, tools=None, **kwargs):
        yield ChatChunk(content="你好，我是回声。")


async def main():
    settings = Settings(provider="echo", model="echo")
    agent = Agent(
        settings.model,
        ToolRegistry(),
        settings,
        provider=EchoProvider(settings.model, settings),
    )
    result = await agent.turn("你好")
    print(result.content)


asyncio.run(main())
```

这个示例不联网，能直接跑通内核的最小闭环。

## Provider 接入

内核只定义抽象，不内置厂商。实现一个 Provider 需要完成两件事：

```text
class MyProvider(Provider):
    def build_tool_messages(self, tool_calls, results):
        # 把工具调用与结果构造成厂商要求的消息格式
        return []

    async def chat(self, messages, tools=None, **kwargs):
        # 调用模型，逐块 yield ChatChunk
        yield ChatChunk(content="...")
```

`ChatChunk` 字段：

- `thinking`：思考过程
- `content`：正文
- `tool_calls`：工具调用
- `done`：流是否结束

两种使用方式：

```text
# 方式一：直接传实例
agent = Agent(model, registry, settings, provider=MyProvider(model, settings))

# 方式二：注册名字
register_provider("my_provider", MyProvider)
settings = Settings(provider="my_provider", model="my-model")
agent = Agent(settings.model, registry, settings)
```

重试、错误归一由内核在抽象层处理，Provider 不需要自己实现。

## 完整对话调用

### 1. 无头回合 `turn()`

```text
result = await agent.turn("你好")
print(result.content)
print(result.tool_calls)
```

`turn()` 内部完成：追加用户消息、跑模型、工具闭环、包还原、写入长期记忆。

### 2. 流式回合 `turn_stream()`

```text
async for event in agent.turn_stream("你好"):
    if event.kind == "content":
        print(event.text, end="", flush=True)
```

事件类型：

- `thinking`：思考片段
- `content`：正文片段
- `tool_calls`：模型请求的工具调用
- `tool_result`：工具执行结果
- `package_restored`：外置包还原
- `done`：回合结束

内核只发原始事件，不做清洗、去重或渲染；think 标签可能出现在 `content` / `thinking`
里，由外壳自己处理。

### 3. 最底层手动流

```text
async for chunk in agent.send_message("你好"):
    print(chunk.content, end="", flush=True)
```

需要自己控制工具闭环时，组合 `execute_tool_calls` 与 `continue_with_tools`。
大多数场景用 `turn()` / `turn_stream()` 就够。

## 会话记忆：换记忆

```text
from pathlib import Path

from yuki_kernel import SessionStore

# 导出
SessionStore.export(session, Path("robot.jsonl"))

# 导入，生成新会话
loaded = SessionStore.import_file(Path("robot.jsonl"), name="robot")

# 给 Agent 换记忆
agent.switch_session(loaded)
```

持久化目录由外部软件传入：

```text
store = SessionStore(Path("/your/data"))
store.save(session)
```

`save / load / list_sessions` 使用 JSONL + SQLite 索引，目录完全由外部决定。

## 长期记忆

```text
from yuki_kernel import MemoryStore

memory = MemoryStore(Path("/your/data"), namespace="robot_a")
memory.add(session_id, "用户：你好\n助手：你好呀")
```

- 按 `namespace` 隔离，多个机器人可以共用内核。
- 模型通过 `search_memory` 工具按需检索，不自动注入。
- 使用 `App` 时，`MemoryStore.search_text` 会自动接到 `search_memory` 上。

## 工具与外置包

```text
from yuki_kernel import ToolRegistry

registry = ToolRegistry(
    packages_dir,          # 外部软件提供包目录
    available=["weather"], # 白名单
    preload=["weather"],   # 启动即加载
)
```

注册表自带元工具：

- `list_packages`：查看可用包
- `load_package` / `unload_package`：按需加载/卸载
- `search_memory`：检索长期记忆

外置包格式见 [docs/tools/manifest.md](tools/manifest.md)。

## 中间件与事件

```text
from yuki_kernel.core.events import EventBus, Middleware


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

内核不读环境变量。`Settings` 由外部软件构造，`provider` 和 `model` 必填：

```text
settings = Settings(
    provider="api",
    model="glm-4.5-air",
    packages_dir=Path("/your/project/packages"),
    data_dir=Path("/your/project/data"),
    retry_max=3,
)
```

常用字段：

- `think`：是否开启思考
- `openai_base_url` / `openai_api_key`：API provider 参数
- `ollama_host` / `ollama_port`：Ollama provider 参数
- `packages` / `packages_preload`：外置包加载策略
- `max_context_tokens` / `keep_recent_messages`：上下文预算
- `memory_limit` / `namespace`：长期记忆
- `retry_max` / `retry_base`：重试

`packages_dir`、`data_dir` 传 `None` 时，内核不加载外置包、不启用持久化记忆。

## 示例 agent：Yuki

仓库里的 `src/yuki/` 是基于内核实现的聊天外壳，作为外部软件参考：

```bash
PYTHONPATH=src .venv/bin/python -m yuki
```

它默认也是空白大脑。要让 Yuki 回答“我是 Yuki”，配置：

```text
AGENT_PACKAGES_PRELOAD=yuki_persona
```

斜杠命令：

- `/save <名字>`、`/load <名字>`、`/sessions`、`/new`
- `/reload`
- `/pkg install|remove|list`

## 外部软件架构建议

内核不规定上层结构。实体机器人可以这样组合：

- 思考层：把传感器/环境状态转成消息，调 `agent.turn()` 生成决策。
- 注意力层：决定把哪些会话、记忆、工具放入 registry 和 session。
- 动作层：消费 `TurnResult.tool_calls`，执行物理/软件动作。

内核提供完整调用面，上层只负责“给什么记忆、给什么工具、怎么用结果”。
