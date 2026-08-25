# 工具系统

Yuki 支持三类工具能力：

| 类型         | 说明                                                                    | 位置                         |
| ------------ | ----------------------------------------------------------------------- | ---------------------------- |
| 内置工具函数 | 随代码分发，声明在 `builtin.py`，实现在 `builtins/`                     | `src/yuki/skills/builtin.py` |
| 外置工具包   | 独立文件夹，通过 `manifest.json` 声明工具，入口可以是 Python 代码或命令 | `packages/`                  |
| 纯提示词包   | 只有提示词，没有可执行代码，提示词注入系统消息                          | `packages/`                  |

## 快速开始

把包目录放进 `packages/`，启动时自动加载：

```bash
yuki
```

外置包默认只被发现，不进入上下文。模型需要某能力时，会先调用
`list_packages` 查看可用包，再调用 `load_package` 加载；不用时可以
`unload_package` 卸载。可以用 `AGENT_PACKAGES_PRELOAD` 让某些包启动时就加载。

当前目录已有三个示例包：

```text
packages/
  weather/          # python 工具 + 提示词
  echo/             # command 命令工具
  writing_style/    # 纯提示词包
```

删除某个目录即可禁用对应工具包。

## 环境变量

| 变量                     | 默认值     | 说明                                                         |
| ------------------------ | ---------- | ------------------------------------------------------------ |
| `PACKAGES_DIR`           | `packages` | 外置工具包所在目录；相对路径按项目根目录解析，也可写绝对路径 |
| `AGENT_PACKAGES`         | 空         | 可用外置包白名单，逗号分隔；留空表示目录下全部可用           |
| `AGENT_PACKAGES_PRELOAD` | 空         | 启动即加载的外置包，逗号分隔；留空表示由模型按需加载         |
| `AGENT_MAX_CONTEXT_TOKENS` | `12000`  | 上下文预算，超限时压缩旧消息                                 |
| `AGENT_KEEP_RECENT_MESSAGES` | `10`   | 摘要时保留的最近消息条数                                     |
| `AGENT_RETRY_MAX`        | `3`        | provider 瞬时错误最大重试次数                                |
| `AGENT_RETRY_BASE`       | `0.5`      | 重试退避基数（秒）                                           |
| `DATA_DIR`               | `data`     | 会话 JSONL 与 SQLite 索引目录                                |

## 提示词如何生效

只有已加载包的 `prompts` 会被拼接进系统消息，因此纯提示词包也能改变模型行为。
比如 `writing_style` 被加载后，模型会收到“回答保持简洁”的提示；卸载后提示词也随之移除。

## 上下文占用

- 内置工具和 `list_packages / load_package / unload_package` 三个目录工具始终在上下文中。
- 外置包的工具 schema 和提示词，只有 `load_package` 加载后才进入上下文。
- 包的执行代码仍然在第一次真正调用工具时才加载。
- 每轮对话结束会把外置包状态还原到本轮开始前：本轮临时加载的包自动卸载，
  `AGENT_PACKAGES_PRELOAD` 预加载的包恢复常驻。

示例：启动时模型只会看到 `get_name` 和三个目录工具；查询天气前会先
`load_package("weather")`，之后 `weather_now` 才出现在工具列表里。

## 内置工具

内置工具不经过 `packages/`，注册表写在 `src/yuki/skills/builtin.py`：

- `BUILTIN_TOOLS`：函数工具，`entry` 格式与外置包一致（支持 python 和 command 入口）。
- `BUILTIN_PROMPTS`：内置提示词，`path` 指向 `builtins/prompts/` 下的 Markdown 文件。

工具实现代码放在 `src/yuki/skills/builtins/`，例如 `people.py`。内置工具
始终在上下文中，不参与外置包的按需加载。

## 安全

外置包可能执行任意 Python 代码或系统命令。加载前请检查包内容，只保留你信任的包。
`command` 入口工具和 manifest 声明 `requires_approval: true` 的工具，执行前需要审批：
`y` 只批一次，`ya` 会话内记住，`y <分钟>` 记住指定时长，`n` 拒绝。

## 会话与包管理命令

- `/save <名字>`：把当前会话写入 `data/sessions/`，索引进 SQLite。
- `/load <名字>` / `/sessions` / `/new`：恢复/列出/新建会话。
- `/reload`：重新加载 `.env` 配置（也会自动监听变化）。
- `/pkg install <目录|zip>` / `/pkg remove <id>` / `/pkg list`：本地包管理。

字段格式完整参考见 [manifest.md](manifest.md)。
