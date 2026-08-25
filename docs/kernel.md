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
        Settings.load(),
    )
    result = await agent.turn("你好")
    print(result.content)


asyncio.run(main())
```

`Agent.turn()` 是一个完整回合：追加用户消息、跑模型、执行工具闭环、还原工具包、
写入长期记忆，最后返回 `TurnResult`。

## 注入人格（后天记忆）

内核本身没有身份。外部软件通过 `system_prompt` 或人格包告诉它“我是谁”：

```text
agent = Agent(
    "glm-4.5-air",
    registry,
    settings,
    system_prompt="你是 Yuki，一个本地运行的 AI 助手。",
)
```

也可以用外置人格包，例如仓库里的 `packages/yuki_persona`，通过
`AGENT_PACKAGES_PRELOAD=yuki_persona` 预加载。

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

`SessionStore.save/load/list_sessions` 负责在 `data/sessions/` 持久化和索引。

## 长期记忆

长期记忆按 `namespace` 隔离，适合多个机器人共用同一个内核：

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
    "packages",
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

外部软件需要自己控制渲染时，可以直接消费流：

```text
async for chunk in agent.send_message("你好"):
    print(chunk.content, end="", flush=True)
```

需要手动跑工具闭环时：

```text
from yuki_kernel.core.stream import collect_stream

out = await collect_stream(agent.send_message(user_input))
while out.tool_calls:
    results = await agent.execute_tool_calls(out.tool_calls)
    out = await collect_stream(agent.continue_with_tools(out.tool_calls, results))
```

大多数场景直接用 `agent.turn()` 更简单。

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

常用环境变量：

- `AGENT_PROVIDER`：`ollama` 或 `api`
- `AGENT_MODEL`：模型名
- `AGENT_THINK`：是否开启思考
- `OPENAI_API_KEY` / `OPENAI_BASE_URL`：API provider
- `PACKAGES_DIR` / `AGENT_PACKAGES` / `AGENT_PACKAGES_PRELOAD`
- `AGENT_MAX_CONTEXT_TOKENS` / `AGENT_KEEP_RECENT_MESSAGES`
- `AGENT_MEMORY_LIMIT` / `AGENT_NAMESPACE`
- `AGENT_RETRY_MAX` / `AGENT_RETRY_BASE`
- `DATA_DIR`

完整说明见 [.env.example](../.env.example)。

## 示例 agent：Yuki

仓库里的 `src/yuki/` 是基于内核实现的聊天外壳，作为外部软件的参考实现：

```bash
PYTHONPATH=src .venv/bin/python -m yuki
```

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
