# 项目规则

## 1. 提交前检查（必须）

每次代码、文档或配置变更提交前，必须依次完成：

1. 跑测试，确认全绿：
   ```bash
   cd kernel && PYTHONPATH=src ../.venv/bin/python -m pytest -q
   cd example && PYTHONPATH=../kernel/src:src ../.venv/bin/python -m pytest -q
   ```
2. 跑 PyCharm 无头检查（根项目限定源码范围，排除 `.venv`），确认退出码为 0：
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

检查进程退出码必须为 0，测试必须全绿。不要跳过。

## 2. 提交格式

- 提交消息遵循 `类型: 描述`，如 `修复:`、`重构:`、`功能:`、`文档:`、`移除:`、`撤回:`。
- 描述用中文，多个要点用分号连接。
- 默认不推送；只有用户明确要求时才推送。

## 3. 架构边界

- `kernel/` 是空白大脑：不自动加载人格/身份，不读环境变量，不持有 `data/`、`packages/` 目录。
- `example/` 负责配置、UI 渲染、审批和进程生命周期，通过依赖调用内核。
- 渲染与内容清洗属于外部 UI 层；尽量保留模型原始数据，不做猜测性改写。
- 内核内置 `openai` / `anthropic` Provider，外部软件可注册自定义 Provider 或直接注入实例。

## 4. 代码组织

- 文件能分类则分类，目录不堆平铺。
- 单文件代码量尽量小，能分发则分发，能组装则组装。
- 改动保持小而聚焦，不顺手重构无关代码。

## 5. 工作区纪律

- 不删除或回滚用户未要求的文件/改动；破坏性命令需要明确授权。
- 不修改与任务无关的文件。
- 生成物不入库：`.venv/`、`data/`、`.idea/`、`uv.lock` 等。
