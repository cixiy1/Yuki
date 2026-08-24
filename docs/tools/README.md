# 工具系统

Yuki 支持三类工具能力：

| 类型 | 说明 | 位置 |
| --- | --- | --- |
| 内置工具函数 | 随代码分发，直接注册 Python handler | `src/yuki/skills/builtin.py` |
| 外置工具包 | 独立文件夹，通过 `manifest.json` 声明工具，入口可以是 Python 代码或命令 | `packages/` |
| 纯提示词包 | 只有提示词，没有可执行代码，提示词注入系统消息 | `packages/` |

## 快速开始

把包目录放进 `packages/`，启动时自动加载：

```bash
yuki
```

当前目录已有三个示例包：

```text
packages/
  weather/          # python 工具 + 提示词
  echo/             # command 命令工具
  writing_style/    # 纯提示词包
```

删除某个目录即可禁用对应工具包。

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PACKAGES_DIR` | `packages` | 外置工具包所在目录 |

## 提示词如何生效

`prompts` 中的提示词会被拼接成系统消息注入对话，因此纯提示词包也能改变模型行为。
比如 `writing_style` 加载后，模型会收到“回答保持简洁”的提示。

## 安全

外置包可能执行任意 Python 代码或系统命令。加载前请检查包内容，只保留你信任的包。

字段格式完整参考见 [manifest.md](manifest.md)。
