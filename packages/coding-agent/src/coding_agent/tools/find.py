"""文件查找工具。

提供基于 glob 模式的文件查找功能。
"""

from __future__ import annotations

import fnmatch
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
    "FindToolDetails",
    "create_find_tool",
]

DEFAULT_LIMIT = 1000


@dataclass
class FindToolDetails:
    """Find 工具执行详情。"""

    truncation: TruncationResult | None = None
    result_limit_reached: int | None = None


def _should_ignore_dir(dir_name: str) -> bool:
    """检查目录是否应该被忽略。"""
    return dir_name.startswith(".") or dir_name in (
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "build",
        "dist",
    )


def _glob_recursive(
    pattern: str,
    search_path: str,
    limit: int,
    results: list[str],
) -> None:
    """递归查找文件。"""
    if len(results) >= limit:
        return

    try:
        entries = os.listdir(search_path)
    except OSError:
        return

    for entry in entries:
        if len(results) >= limit:
            return

        if entry.startswith("."):
            continue

        full_path = os.path.join(search_path, entry)

        if os.path.isdir(full_path):
            if _should_ignore_dir(entry):
                continue
            _glob_recursive(pattern, full_path, limit, results)
        elif os.path.isfile(full_path):
            rel_path = os.path.relpath(full_path, search_path)
            if fnmatch.fnmatch(entry, pattern) or fnmatch.fnmatch(rel_path, pattern):
                results.append(full_path)


def _to_posix_path(value: str) -> str:
    """转换为 POSIX 路径格式。"""
    return value.replace(os.sep, "/")


def create_find_tool(cwd: str) -> dict[str, Any]:
    """创建 find 工具。

    Args:
        cwd: 工作目录。

    Returns:
        工具定义字典。

    """

    def execute(
        tool_call_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """执行 find 命令。"""
        pattern: str = params.get("pattern", "")
        search_dir_input: str = params.get("path", ".")
        limit: int | None = params.get("limit")
        effective_limit = limit if limit is not None else DEFAULT_LIMIT

        search_path = resolve_to_cwd(search_dir_input, cwd)

        if not os.path.exists(search_path):
            raise ValueError(f"路径不存在: {search_path}")

        # 递归查找
        results: list[str] = []

        # 处理 **/ 前缀
        if pattern.startswith("**/"):
            pattern = pattern[3:]

        _glob_recursive(pattern, search_path, effective_limit, results)

        if not results:
            return {
                "content": [{"type": "text", "text": "未找到匹配的文件"}],
                "details": None,
            }

        # 转换为相对路径
        relativized: list[str] = []
        for p in results:
            if p.startswith(search_path):
                rel = p[len(search_path) + 1 :]
            else:
                rel = os.path.relpath(p, search_path)
            relativized.append(_to_posix_path(rel))

        result_limit_reached = len(relativized) >= effective_limit

        # 应用截断
        raw_output = "\n".join(relativized)
        truncation = truncate_head(raw_output, max_lines=999999)

        output = truncation.content
        details: dict[str, Any] = {}
        notices: list[str] = []

        if result_limit_reached:
            notices.append(
                f"{effective_limit} 结果限制 reached。使用 limit={effective_limit * 2} 查看更多，或优化模式"
            )
            details["result_limit_reached"] = effective_limit

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
        "name": "find",
        "label": "find",
        "description": f"通过 glob 模式搜索文件。返回匹配的文件路径（相对于搜索目录）。遵循 .gitignore。输出被截断到 {DEFAULT_LIMIT} 结果或 {DEFAULT_MAX_BYTES // 1024}KB（以先达到者为准）。",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob 模式，如 '*.py'、'**/*.json' 或 'src/**/*.test.py'",
                },
                "path": {"type": "string", "description": "搜索目录（默认：当前目录）"},
                "limit": {"type": "integer", "description": "最大结果数（默认：1000）"},
            },
            "required": ["pattern"],
        },
        "execute": execute,
    }


def find_tool(cwd: str | None = None) -> dict[str, Any]:
    """创建默认 find 工具（使用当前工作目录）。

    Args:
        cwd: 工作目录，默认为当前目录。

    Returns:
        Find 工具定义。

    """
    return create_find_tool(cwd or os.getcwd())
