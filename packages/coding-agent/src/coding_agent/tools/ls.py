"""目录列表工具。

提供目录内容列表功能。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from coding_agent.tools.path_utils import resolve_to_cwd
from coding_agent.tools.truncate import (
    DEFAULT_MAX_BYTES,
    TruncationResult,
    format_size,
    truncate_head,
)

__all__ = [
    "LsToolDetails",
    "create_ls_tool",
]

DEFAULT_LIMIT = 500


@dataclass
class LsToolDetails:
    """Ls 工具执行详情。"""

    truncation: TruncationResult | None = None
    entry_limit_reached: int | None = None


def create_ls_tool(cwd: str) -> dict[str, Any]:
    """创建 ls 工具。

    Args:
        cwd: 工作目录。

    Returns:
        工具定义字典。

    """

    def execute(
        tool_call_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """执行 ls 命令。"""
        dir_path_input: str = params.get("path", ".")
        limit: int | None = params.get("limit")
        effective_limit = limit if limit is not None else DEFAULT_LIMIT

        dir_path = resolve_to_cwd(dir_path_input, cwd)

        # 检查路径是否存在
        if not os.path.exists(dir_path):
            raise ValueError(f"路径不存在: {dir_path}")

        # 检查是否为目录
        if not os.path.isdir(dir_path):
            raise ValueError(f"不是目录: {dir_path}")

        # 读取目录条目
        try:
            entries = os.listdir(dir_path)
        except OSError as e:
            raise ValueError(f"无法读取目录: {e}") from e

        # 按字母顺序排序（不区分大小写）
        entries.sort(key=lambda x: x.lower())

        # 格式化条目（添加目录标记）
        results: list[str] = []
        entry_limit_reached = False

        for entry in entries:
            if len(results) >= effective_limit:
                entry_limit_reached = True
                break

            full_path = os.path.join(dir_path, entry)
            suffix = ""

            try:
                if os.path.isdir(full_path):
                    suffix = "/"
            except OSError:
                continue

            results.append(entry + suffix)

        if not results:
            return {"content": [{"type": "text", "text": "(空目录)"}], "details": None}

        # 应用截断
        raw_output = "\n".join(results)
        truncation = truncate_head(raw_output, max_lines=999999)

        output = truncation.content
        details: dict[str, Any] = {}
        notices: list[str] = []

        if entry_limit_reached:
            notices.append(
                f"{effective_limit} 条目限制 reached。使用 limit={effective_limit * 2} 查看更多"
            )
            details["entry_limit_reached"] = effective_limit

        if truncation.truncated:
            notices.append(f"{format_size(DEFAULT_MAX_BYTES)} 限制 reached")
            details["truncation"] = truncation

        if notices:
            output += f"\n\n[{'. '.join(notices)}]"

        return {
            "content": [{"type": "text", "text": output}],
            "details": details if details else None,
        }

    return {
        "name": "ls",
        "label": "ls",
        "description": f"列出目录内容。返回按字母顺序排序的条目，目录以 '/' 结尾。包含隐藏文件。输出被截断到 {DEFAULT_LIMIT} 条目或 {DEFAULT_MAX_BYTES // 1024}KB（以先达到者为准）。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "要列出的目录（默认：当前目录）"},
                "limit": {"type": "integer", "description": "返回的最大条目数（默认：500）"},
            },
        },
        "execute": execute,
    }


def ls_tool(cwd: str | None = None) -> dict[str, Any]:
    """创建默认 ls 工具（使用当前工作目录）。

    Args:
        cwd: 工作目录，默认为当前目录。

    Returns:
        Ls 工具定义。

    """
    return create_ls_tool(cwd or os.getcwd())
