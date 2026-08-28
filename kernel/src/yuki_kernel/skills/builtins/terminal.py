"""内置工具：在终端/shell 里执行命令。

走内核现有 Sandbox：默认降权（user="nobody"），调用方可传 sandbox: false
关闭降权。降权是否真正生效由运行时环境与注入的 Sandbox 实现决定（强隔离
由宿主外部软件设置，内核不自行判断权限）。handler 在子进程内自行构造
Sandbox 实例，故参数级开关可独立生效。

注意：该模块经 executor 的子进程引导脚本以 spec_from_file_location 加载，
无包上下文，故需先把内核 src 目录加入 sys.path 才能导入 yuki_kernel 内部模块。
"""

import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent.parent.parent.parent)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from yuki_kernel.skills.sandbox import BasicSandbox, RunResult, SandboxConfig


def run_terminal(cmd: str, sandbox: bool = True) -> str:
    """在 shell 中执行命令并返回结果文本。

    cmd: 要执行的命令字符串（经 /bin/sh -c 运行，适配各 POSIX 终端）。
    sandbox: 是否降权执行，默认 True；设为 False 仅在可信环境关闭。
    """
    if not cmd or not cmd.strip():
        return "错误：命令为空"
    config = SandboxConfig(user="nobody" if sandbox else None)
    box: BasicSandbox = BasicSandbox(config)
    run: RunResult = box.run(
        command=["/bin/sh", "-c", cmd],
        cwd=Path.cwd(),
        input_text="",
        timeout=30,
        env=None,
    )
    parts = [f"退出码: {run.returncode}"]
    if run.stdout.strip():
        parts.append(f"标准输出:\n{run.stdout.strip()}")
    if run.stderr.strip():
        parts.append(f"标准错误:\n{run.stderr.strip()}")
    if run.returncode != 0 and not run.stdout.strip() and not run.stderr.strip():
        parts.append("(无输出)")
    return "\n".join(parts)
