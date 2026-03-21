"""Bash 命令执行模块 - 对齐 pi-mono TypeScript 实现

提供带流式支持和取消功能的 bash 命令执行。
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from coding_agent.tools.truncate import truncate_tail, DEFAULT_MAX_BYTES


@dataclass
class BashResult:
    """Bash 执行结果

    属性：
        output: 合并的 stdout + stderr 输出（已清理，可能被截断）
        exit_code: 进程退出码（如果被终止/取消则为 None）
        cancelled: 是否通过信号取消
        truncated: 输出是否被截断
        full_output_path: 包含完整输出的临时文件路径（如果输出超过截断阈值）
    """

    output: str
    exit_code: int | None
    cancelled: bool
    truncated: bool
    full_output_path: str | None = None


def execute_bash(
    command: str,
    on_chunk: Callable[[str], None] | None = None,
    signal: Any | None = None,
    cwd: str | None = None,
) -> BashResult:
    """执行 bash 命令

    Args:
        command: 要执行的 bash 命令
        on_chunk: 流式输出回调（已清理）
        signal: AbortSignal 用于取消
        cwd: 工作目录

    Returns:
        BashResult 执行结果
    """
    cwd = cwd or str(Path.cwd())

    if not os.path.exists(cwd):
        raise ValueError(f"工作目录不存在: {cwd}")

    output_chunks: list[str] = []
    output_bytes = 0
    max_output_bytes = DEFAULT_MAX_BYTES * 2

    def collect_chunk(chunk: str) -> None:
        """收集输出块"""
        nonlocal output_bytes
        output_chunks.append(chunk)
        output_bytes += len(chunk)

        while output_bytes > max_output_bytes and len(output_chunks) > 1:
            removed = output_chunks.pop(0)
            output_bytes -= len(removed)

        if on_chunk:
            on_chunk(chunk)

    cancelled = False
    shell = os.environ.get("SHELL", "/bin/bash")
    full_command = [shell, "-c", command]
    process: subprocess.Popen[bytes] | None = None

    try:
        process = subprocess.Popen(
            full_command,
            cwd=cwd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=dict(os.environ),
            start_new_session=True,
        )

        if process.stdout is None:
            raise RuntimeError("Failed to open stdout pipe")
        while True:
            data: bytes = process.stdout.read(4096)
            if not data:
                break
            chunk: str = data.decode("utf-8", errors="replace")
            collect_chunk(chunk)

            if signal is not None and hasattr(signal, "aborted") and signal.aborted:
                cancelled = True
                break

        process.wait()
        exit_code = process.returncode

        if cancelled:
            try:
                os.killpg(os.getpgid(process.pid), 15)
                process.wait(timeout=1)
            except Exception:
                pass
            exit_code = None

    except Exception:
        if process is not None and process.poll() is None:
            try:
                os.killpg(os.getpgid(process.pid), 15)
                process.wait(timeout=1)
            except Exception:
                pass
        raise

    full_output = "".join(output_chunks)
    truncation = truncate_tail(full_output)

    return BashResult(
        output=truncation.content if truncation.truncated else full_output,
        exit_code=exit_code,
        cancelled=cancelled,
        truncated=truncation.truncated,
    )


__all__ = [
    "BashResult",
    "execute_bash",
]
