"""Bash 命令执行模块 - 对齐 pi-mono TypeScript 实现

提供带流式支持和取消功能的 bash 命令执行。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from coding_agent.tools.bash import create_bash_tool
from coding_agent.tools.truncate import truncate_tail, DEFAULT_MAX_BYTES


# ============================================================================
# 类型定义
# ============================================================================


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


# ============================================================================
# 执行函数
# ============================================================================


def execute_bash(
    command: str,
    on_chunk: Callable[[str], None] | None = None,
    signal: Any | None = None,
    cwd: str | None = None,
) -> BashResult:
    """执行 bash 命令

    使用与 create_bash_tool() 相同的本地 BashOperations 后端，
    确保交互式用户 bash 和工具调用的 bash 共享相同的进程派生行为。

    Args:
        command: 要执行的 bash 命令
        on_chunk: 流式输出回调（已清理）
        signal: AbortSignal 用于取消
        cwd: 工作目录

    Returns:
        BashResult 执行结果
    """
    cwd = cwd or str(Path.cwd())

    # 使用工具执行
    bash_tool = create_bash_tool(cwd)

    output_chunks: list[str] = []
    output_bytes = 0
    max_output_bytes = DEFAULT_MAX_BYTES * 2

    def collect_chunk(chunk: str) -> None:
        """收集输出块"""
        nonlocal output_bytes
        output_chunks.append(chunk)
        output_bytes += len(chunk)

        # 保持滚动缓冲区
        while output_bytes > max_output_bytes and len(output_chunks) > 1:
            removed = output_chunks.pop(0)
            output_bytes -= len(removed)

        # 流式回调
        if on_chunk:
            on_chunk(chunk)

    # 执行命令
    try:
        # 通过工具执行
        result = bash_tool["execute"](command)

        # 处理输出
        output = result.get("output", "")
        if output:
            collect_chunk(output)

        # 截断处理
        full_output = "".join(output_chunks)
        truncation = truncate_tail(full_output)

        # 检查是否被取消
        cancelled = bool(signal and hasattr(signal, "aborted") and signal.aborted)

        return BashResult(
            output=truncation.content if truncation.truncated else full_output,
            exit_code=None if cancelled else result.get("exitCode"),
            cancelled=cancelled,
            truncated=truncation.truncated,
        )

    except Exception:
        # 检查是否是被取消
        if signal and hasattr(signal, "aborted") and signal.aborted:
            full_output = "".join(output_chunks)
            truncation = truncate_tail(full_output)
            return BashResult(
                output=truncation.content if truncation.truncated else full_output,
                exit_code=None,
                cancelled=True,
                truncated=truncation.truncated,
            )
        raise


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "BashResult",
    "execute_bash",
]
