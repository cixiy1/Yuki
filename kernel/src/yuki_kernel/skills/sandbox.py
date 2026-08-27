"""工具执行沙箱：默认纯标准库实现，给外部工具加一层 OS 级安全阀门。

设计要点：
- 进程内不再直接 exec 任意 Python；python 工具也经子进程执行，与 command 共用沙箱。
- BasicSandbox 不引入新依赖：可降权到无特权用户、限制 CPU/内存/文件大小、清空环境、
  对 command 入口做命令白名单。
- 强隔离（firejail/nsjail/容器/seccomp 断网）留给宿主自行实现 Sandbox 接口后注入。

注意：子进程默认继承当前用户权限。沙箱降低的是「工具能干什么」的上限，不是替代
宿主对包来源的信任审查。仍只加载你信任的包。
"""

from __future__ import annotations

import contextlib
import os
import pwd
import resource
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SandboxConfig:
    """BasicSandbox 的阀门配置。"""

    user: Optional[str] = None  # 降级到的无特权系统用户，如 "nobody"；None=不降权
    cpu_seconds: int = 10  # CPU 时间上限（秒）
    memory_bytes: int = 256 * 1024 * 1024  # 地址空间上限（字节）
    file_bytes: int = 10 * 1024 * 1024  # 单个文件写入上限（字节）
    allowed_binaries: Optional[list[str]] = None  # command 入口可执行文件白名单；None=不限制
    extra_env: dict[str, str] = field(default_factory=dict)  # 注入子进程的环境变量


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str


class Sandbox:
    """沙箱接口；自定义实现只需替换 run 即可注入更强的隔离。"""

    def run(
        self,
        command: list[str],
        cwd: Path,
        input_text: str,
        timeout: float = 30,
    ) -> RunResult:
        raise NotImplementedError


class BasicSandbox(Sandbox):
    """纯标准库的默认沙箱：降权 + 资源上限 + 命令白名单 + 清空环境。"""

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()

    def _preexec(self) -> None:
        cfg = self.config
        if cfg.user:
            try:
                pw = pwd.getpwnam(cfg.user)
            except KeyError:
                return
            # 先组后用户，避免丢失组查找能力
            os.setgid(pw.pw_gid)
            os.setuid(pw.pw_uid)
        with contextlib.suppress(ValueError, OSError):
            resource.setrlimit(resource.RLIMIT_CPU, (cfg.cpu_seconds, cfg.cpu_seconds))
        with contextlib.suppress(ValueError, OSError):
            resource.setrlimit(resource.RLIMIT_AS, (cfg.memory_bytes, cfg.memory_bytes))
        with contextlib.suppress(ValueError, OSError):
            resource.setrlimit(resource.RLIMIT_FSIZE, (cfg.file_bytes, cfg.file_bytes))

    def run(
        self,
        command: list[str],
        cwd: Path,
        input_text: str,
        timeout: float = 30,
    ) -> RunResult:
        cfg = self.config
        if not command:
            return RunResult(1, "", "空命令")
        if cfg.allowed_binaries is not None and command[0] not in cfg.allowed_binaries:
            return RunResult(1, "", f"命令不在白名单：{command[0]}")
        try:
            proc = subprocess.run(
                command,
                cwd=cwd,
                input=input_text,
                text=True,
                capture_output=True,
                timeout=timeout,
                env=dict(cfg.extra_env) if cfg.extra_env else {},
                preexec_fn=self._preexec,
            )
        except subprocess.TimeoutExpired:
            return RunResult(1, "", "工具执行超时")
        except Exception as err:  # noqa: BLE001 - 工具执行失败需回喂模型而非崩溃
            return RunResult(1, "", f"工具执行失败：{err}")
        return RunResult(proc.returncode, proc.stdout, proc.stderr)
