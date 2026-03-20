"""Bash 执行工具.

提供安全、可控的 bash 命令执行功能。
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from typing import IO, Any, Protocol

from agent import AgentTool, AgentToolResult
from ai.types import TextContent

from coding_agent.tools.truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    TruncationResult,
    format_size,
    truncate_tail,
)

__all__ = [
    "BashToolDetails",
    "BashOperations",
    "BashSpawnContext",
    "BashSpawnHook",
    "BashToolOptions",
    "create_bash_tool",
]


@dataclass
class BashToolDetails:
    """Bash 工具执行详情."""

    truncation: TruncationResult | None = None
    full_output_path: str | None = None


class BashOperations(Protocol):
    """Bash 操作协议."""

    def exec(
        self,
        command: str,
        cwd: str,
        on_data: Callable[[bytes], None],
        abort_signal: Any = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """执行命令并流式输出."""
        ...


class BashSpawnContext:
    """Bash 执行上下文."""

    def __init__(self, command: str, cwd: str, env: dict[str, str]) -> None:
        """初始化上下文."""
        self.command = command
        self.cwd = cwd
        self.env = env


BashSpawnHook = Callable[[BashSpawnContext], BashSpawnContext]


@dataclass
class BashToolOptions:
    """Bash 工具选项."""

    operations: BashOperations | None = None
    command_prefix: str | None = None
    spawn_hook: BashSpawnHook | None = None


def _get_shell_config() -> tuple[str, list[str]]:
    """获取 shell 配置."""
    shell = os.environ.get("SHELL", "/bin/bash")
    return shell, ["-c"]


def _get_shell_env() -> dict[str, str]:
    """获取 shell 环境变量."""
    return dict(os.environ)


def _get_temp_file_path() -> str:
    """生成临时文件路径."""
    fd, path = tempfile.mkstemp(prefix="bash-tool-", suffix=".log")
    os.close(fd)
    return path


class _LocalBashOperations:
    """本地 bash 操作实现."""

    def exec(
        self,
        command: str,
        cwd: str,
        on_data: Callable[[bytes], None],
        abort_signal: Any = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """执行命令."""
        import signal as signal_module

        if not os.path.exists(cwd):
            raise ValueError(f"工作目录不存在: {cwd}")

        shell, args = _get_shell_config()
        full_command = f"{shell} {' '.join(args)} '{command}'"

        process = subprocess.Popen(
            full_command,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )

        timed_out = False
        aborted = False

        def timeout_handler(signum: int, frame: Any) -> None:
            nonlocal timed_out
            timed_out = True
            if process.poll() is None:
                os.killpg(os.getpgid(process.pid), signal_module.SIGTERM)

        old_handler = None
        if timeout and timeout > 0:
            old_handler = signal_module.signal(signal_module.SIGALRM, timeout_handler)
            signal_module.alarm(timeout)

        try:
            if process.stdout:
                while True:
                    data = process.stdout.read(4096)
                    if not data:
                        break
                    if (
                        abort_signal is not None
                        and hasattr(abort_signal, "cancelled")
                        and abort_signal.cancelled
                    ):
                        aborted = True
                        break
                    on_data(data)

            process.wait()

            if old_handler:
                signal_module.alarm(0)
                signal_module.signal(signal_module.SIGALRM, old_handler)

            if aborted:
                raise asyncio.CancelledError("aborted")
            if timed_out:
                raise TimeoutError(f"timeout:{timeout}")

            return {"exit_code": process.returncode}

        except Exception:
            if process.poll() is None:
                try:
                    os.killpg(os.getpgid(process.pid), signal_module.SIGTERM)
                    process.wait(timeout=1)
                except Exception:
                    try:
                        os.killpg(os.getpgid(process.pid), signal_module.SIGKILL)
                    except Exception:
                        pass
            raise


def _create_local_bash_operations() -> BashOperations:
    """创建本地 bash 操作实现."""
    return _LocalBashOperations()


def create_local_bash_operations() -> BashOperations:
    """创建本地 bash 操作实现（公开接口）."""
    return _LocalBashOperations()


def _resolve_spawn_context(
    command: str,
    cwd: str,
    spawn_hook: BashSpawnHook | None = None,
) -> BashSpawnContext:
    """解析执行上下文."""
    base_context = BashSpawnContext(command, cwd, _get_shell_env())
    if spawn_hook:
        return spawn_hook(base_context)
    return base_context


class _BashTool:
    """Bash 工具实现类."""

    def __init__(
        self,
        cwd: str,
        operations: BashOperations,
        command_prefix: str | None = None,
        spawn_hook: BashSpawnHook | None = None,
    ) -> None:
        """初始化 bash 工具.

        Args:
            cwd: 工作目录.
            operations: 命令执行操作.
            command_prefix: 命令前缀.
            spawn_hook: 执行钩子.

        """
        self._cwd = cwd
        self._operations = operations
        self._command_prefix = command_prefix
        self._spawn_hook = spawn_hook

        self.name = "bash"
        self.label = "bash"
        self.description = f"在指定工作目录执行 bash 命令。返回 stdout 和 stderr。输出被截断到最后 {DEFAULT_MAX_LINES} 行或 {DEFAULT_MAX_BYTES // 1024}KB（以先达到者为准）。如果截断，完整输出会保存到临时文件。可选提供超时时间（秒）。"
        self.parameters = {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的 bash 命令"},
                "timeout": {"type": "integer", "description": "超时时间（秒，可选，无默认超时）"},
            },
            "required": ["command"],
        }

    def _check_cancelled(self, signal: Any | None) -> None:
        """检查是否已取消，如已取消则引发 CancelledError."""
        if signal is not None and hasattr(signal, "cancelled") and signal.cancelled:
            raise asyncio.CancelledError("操作已取消")

    def _error_result(
        self, message: str, details: BashToolDetails | None = None
    ) -> AgentToolResult[BashToolDetails]:
        """返回错误结果."""
        return AgentToolResult(
            content=[TextContent(text=message)],
            details=details,
        )

    async def execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any = None,
        on_update: Any = None,
    ) -> AgentToolResult[BashToolDetails]:
        """执行 bash 命令.

        Args:
            tool_call_id: 工具调用ID。
            params: 参数字典（包含 command, timeout）。
            signal: 取消信号（可选）。
            on_update: 进度更新回调（可选）。

        Returns:
            工具执行结果。错误时返回错误内容，不抛出异常。

        """
        command: str = params.get("command", "")
        timeout: int | None = params.get("timeout")

        resolved_command = f"{self._command_prefix}\n{command}" if self._command_prefix else command
        spawn_context = _resolve_spawn_context(resolved_command, self._cwd, self._spawn_hook)

        chunks: list[bytes] = []
        chunks_bytes = 0
        max_chunks_bytes = DEFAULT_MAX_BYTES * 2
        temp_file_path: str | None = None
        temp_file: IO[str] | None = None
        total_bytes = 0

        def handle_data(data: bytes) -> None:
            """处理输出数据."""
            nonlocal total_bytes, temp_file_path, temp_file, chunks_bytes
            total_bytes += len(data)

            if total_bytes > DEFAULT_MAX_BYTES and not temp_file_path:
                temp_file_path = _get_temp_file_path()
                temp_file = open(temp_file_path, "w", encoding="utf-8")
                for chunk in chunks:
                    temp_file.write(chunk.decode("utf-8", errors="replace"))

            if temp_file:
                temp_file.write(data.decode("utf-8", errors="replace"))

            chunks.append(data)
            chunks_bytes += len(data)

            while chunks_bytes > max_chunks_bytes and len(chunks) > 1:
                removed = chunks.pop(0)
                chunks_bytes -= len(removed)

            if on_update:
                full_buffer = b"".join(chunks)
                full_text = full_buffer.decode("utf-8", errors="replace")
                truncation = truncate_tail(full_text)
                on_update(
                    AgentToolResult(
                        content=[TextContent(text=truncation.content or "")],
                        details=BashToolDetails(
                            truncation=truncation if truncation.truncated else None,
                            full_output_path=temp_file_path,
                        ),
                    )
                )

        try:
            result = self._operations.exec(
                spawn_context.command,
                spawn_context.cwd,
                handle_data,
                signal,
                timeout,
                spawn_context.env,
            )

            if temp_file:
                temp_file.close()

            full_buffer = b"".join(chunks)
            full_output = full_buffer.decode("utf-8", errors="replace")

            truncation = truncate_tail(full_output)
            output_text = truncation.content if truncation.content else "(无输出)"

            details: BashToolDetails | None = None
            if truncation.truncated:
                details = BashToolDetails(
                    truncation=truncation,
                    full_output_path=temp_file_path,
                )

                start_line = truncation.total_lines - truncation.output_lines + 1
                end_line = truncation.total_lines

                if truncation.last_line_partial:
                    last_line = full_output.split("\n")[-1] if full_output else ""
                    last_line_size = format_size(len(last_line.encode("utf-8")))
                    output_text += f"\n\n[显示第 {end_line} 行的最后 {format_size(truncation.output_bytes)}（该行共 {last_line_size}）。完整输出: {temp_file_path}]"
                elif truncation.truncated_by == "lines":
                    output_text += f"\n\n[显示第 {start_line}-{end_line} 行（共 {truncation.total_lines} 行）。完整输出: {temp_file_path}]"
                else:
                    output_text += f"\n\n[显示第 {start_line}-{end_line} 行（共 {truncation.total_lines} 行），限制 {format_size(DEFAULT_MAX_BYTES)}。完整输出: {temp_file_path}]"

            exit_code = result.get("exit_code")
            if exit_code is not None and exit_code != 0:
                output_text += f"\n\n命令退出码: {exit_code}"
                return self._error_result(output_text, details)

            return AgentToolResult(
                content=[TextContent(text=output_text)],
                details=details,
            )

        except asyncio.CancelledError:
            if temp_file:
                temp_file.close()
            raise
        except TimeoutError as e:
            if temp_file:
                temp_file.close()
            full_buffer = b"".join(chunks)
            output = full_buffer.decode("utf-8", errors="replace")
            if output:
                output += "\n\n"
            output += f"命令超时（{timeout} 秒）"
            return self._error_result(output)
        except Exception as e:
            if temp_file:
                temp_file.close()
            error_msg = str(e)
            if "aborted" in error_msg.lower():
                full_buffer = b"".join(chunks)
                output = full_buffer.decode("utf-8", errors="replace")
                if output:
                    output += "\n\n"
                output += "命令已中止"
                return self._error_result(output)
            return self._error_result(f"命令执行失败: {e}")


def create_bash_tool(
    cwd: str,
    options: BashToolOptions | None = None,
) -> AgentTool:
    """创建 bash 工具.

    Args:
        cwd: 工作目录。
        options: 工具选项。

    Returns:
        bash 工具实例。

    """
    ops = options.operations if options and options.operations else _create_local_bash_operations()
    command_prefix = options.command_prefix if options else None
    spawn_hook = options.spawn_hook if options else None

    return _BashTool(
        cwd=cwd,
        operations=ops,
        command_prefix=command_prefix,
        spawn_hook=spawn_hook,
    )


def bash_tool() -> AgentTool:
    """创建默认 bash 工具（使用当前工作目录）.

    Returns:
        bash 工具实例。

    """
    return create_bash_tool(os.getcwd())
