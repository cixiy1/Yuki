# Yuki 项目协作规范

这份文件同时写给人和 AI：AI 在改代码、提交前按这里执行；人类同事在 review、接手项目时也用它对齐预期。有冲突时，以这份文件为准。

## 项目结构

- `kernel/`：`yuki_kernel` 内核，空白大脑，可嵌入任何软件。
- `example/`：`yuki` 示例外壳，展示如何调用内核做完整聊天应用。
- `docs/`：内核与工具系统的使用文档。

## 怎么跑测试

内核和示例是两个独立项目，分别验证：

```bash
cd kernel && PYTHONPATH=src ../.venv/bin/python -m pytest -q
cd example && PYTHONPATH=../kernel/src:src ../.venv/bin/python -m pytest -q
```

改动后测试必须全绿。

## 提交前检查

每次代码、文档或配置变更提交前，必须完成：

1. 跑上面的测试，确认全绿。
2. 跑 PyCharm 无头检查，确认退出码为 0：

```bash
rm -rf /tmp/yuki-inspect /tmp/pycharm-config-yuki /tmp/pycharm-system-yuki /tmp/pycharm-log-yuki
mkdir -p /tmp/pycharm-system-yuki /tmp/pycharm-log-yuki
cp -R "$HOME/Library/Application Support/JetBrains/PyCharm2026.2" /tmp/pycharm-config-yuki
find /tmp/pycharm-config-yuki -name '*.lock' -delete
PYCHARM_VM_OPTIONS="$PWD/.pycharm-inspect.vmoptions" \
  /Applications/it/ide/PyCharm.app/Contents/bin/inspect.sh \
  "$PWD" Default /tmp/yuki-inspect \
  -d "$PWD/kernel/src" \
  -d "$PWD/kernel/tests" \
  -d "$PWD/example/src" \
  -d "$PWD/example/tests"
```

这条检查的目的是避免把 PyCharm 能看出来的问题提交进去。不要跳过。

## 提交格式

提交消息用 `类型: 描述`，中文描述，多个要点用分号连接：

```text
修复: 审批参数丢失，外部回调现在能拿到真实参数
文档: 重写内核使用指南，补充三种 Provider 接入方式
重构: 拆分 CLI 职责到 commands/approver/rendering
```

常用类型：`修复:`、`重构:`、`功能:`、`文档:`、`移除:`、`撤回:`。

默认不推送，只有明确要求时才推送。

## 架构约定

改代码前先理解这几条边界，不要越过：

- 内核是空白大脑：不自动加载人格/身份，不读环境变量，不持有 `data/`、`packages/` 目录。
- 示例负责配置、UI 渲染、审批和进程生命周期，通过依赖调用内核。
- 渲染与内容清洗属于外部 UI 层；尽量保留模型原始数据，不做猜测性改写。
- 内核内置 `openai` / `anthropic` Provider；外部软件可以注册自定义 Provider，也可以直接注入实例。

## 代码风格

- 文件能分类则分类，目录不堆平铺。
- 单文件代码量尽量小，能分发则分发，能组装则组装。
- 改动小而聚焦，不顺手重构无关代码。

## 工作区注意事项

- 不删除或回滚他人未要求的文件/改动；破坏性命令先确认。
- 不修改与任务无关的文件。
- 生成物不入库：`.venv/`、`data/`、`.idea/`、`uv.lock` 等。
