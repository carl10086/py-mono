"""内容搜索工具。

提供基于正则表达式的文件内容搜索功能。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from coding_agent.tools.path_utils import resolve_to_cwd
from coding_agent.tools.truncate import (
    DEFAULT_MAX_BYTES,
    GREP_MAX_LINE_LENGTH,
    TruncationResult,
    format_size,
    truncate_head,
    truncate_line,
)

__all__ = [
    "GrepToolDetails",
    "create_grep_tool",
]

DEFAULT_LIMIT = 100


@dataclass
class GrepToolDetails:
    """Grep 工具执行详情。"""

    truncation: TruncationResult | None = None
    match_limit_reached: int | None = None
    lines_truncated: bool = False


def _should_ignore_file(file_path: str) -> bool:
    """检查文件是否应该被忽略。"""
    ignore_patterns = [
        "/node_modules/",
        "/.git/",
        "/__pycache__/",
        "/.venv/",
        "/venv/",
        "/build/",
        "/dist/",
        ".pyc",
        ".pyo",
    ]
    for pattern in ignore_patterns:
        if pattern in file_path:
            return True
    return False


def _search_in_file(
    file_path: str,
    pattern: str,
    ignore_case: bool,
    literal: bool,
) -> list[tuple[int, str]]:
    """在单个文件中搜索。

    Returns:
        匹配列表，每项为 (行号, 行内容)。

    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    matches: list[tuple[int, str]] = []

    # 编译正则
    flags = re.IGNORECASE if ignore_case else 0
    if literal:
        regex = re.compile(re.escape(pattern), flags)
    else:
        try:
            regex = re.compile(pattern, flags)
        except re.error:
            return []

    for i, line in enumerate(lines, 1):
        if regex.search(line):
            matches.append((i, line))

    return matches


def _format_match_with_context(
    file_path: str,
    line_number: int,
    lines: list[str],
    context: int,
    is_directory: bool,
    search_path: str,
) -> tuple[list[str], bool]:
    """格式化匹配项及其上下文。

    Returns:
        (输出行列表, 是否有行被截断)

    """
    output: list[str] = []
    lines_truncated = False

    # 计算相对路径
    if is_directory and file_path.startswith(search_path):
        rel_path = file_path[len(search_path) + 1 :]
    else:
        rel_path = os.path.basename(file_path)

    rel_path = rel_path.replace(os.sep, "/")

    # 上下文范围
    start = max(1, line_number - context)
    end = min(len(lines), line_number + context)

    for current in range(start, end + 1):
        line_text = lines[current - 1] if current <= len(lines) else ""
        sanitized = line_text.replace("\r", "")
        is_match_line = current == line_number

        # 截断长行
        truncated_text, was_truncated = truncate_line(sanitized)
        if was_truncated:
            lines_truncated = True

        if is_match_line:
            output.append(f"{rel_path}:{current}: {truncated_text}")
        else:
            output.append(f"{rel_path}-{current}- {truncated_text}")

    return output, lines_truncated


def create_grep_tool(cwd: str) -> dict[str, Any]:
    """创建 grep 工具。

    Args:
        cwd: 工作目录。

    Returns:
        工具定义字典。

    """

    def execute(
        tool_call_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """执行 grep 命令。"""
        pattern: str = params.get("pattern", "")
        search_path_input: str = params.get("path", ".")
        glob_pattern: str | None = params.get("glob")
        ignore_case: bool = params.get("ignoreCase", False)
        literal: bool = params.get("literal", False)
        context: int = params.get("context", 0)
        limit: int | None = params.get("limit")
        effective_limit = limit if limit is not None else DEFAULT_LIMIT

        search_path = resolve_to_cwd(search_path_input, cwd)

        # 检查路径是否存在
        if not os.path.exists(search_path):
            raise ValueError(f"路径不存在: {search_path}")

        is_directory = os.path.isdir(search_path)

        # 收集要搜索的文件
        files_to_search: list[str] = []

        if is_directory:
            for root, dirs, files in os.walk(search_path):
                # 跳过忽略目录
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ("node_modules", ".git", "__pycache__", ".venv", "venv")
                ]

                for file in files:
                    if file.startswith("."):
                        continue

                    file_path = os.path.join(root, file)

                    if _should_ignore_file(file_path):
                        continue

                    # 检查 glob 模式
                    if glob_pattern:
                        import fnmatch

                        rel_path = os.path.relpath(file_path, search_path)
                        if not fnmatch.fnmatch(rel_path, glob_pattern):
                            continue

                    files_to_search.append(file_path)
        else:
            files_to_search = [search_path]

        # 搜索匹配
        all_matches: list[tuple[str, int, str]] = []
        for file_path in files_to_search:
            if len(all_matches) >= effective_limit:
                break

            matches = _search_in_file(
                file_path,
                pattern,
                ignore_case,
                literal,
            )

            for line_num, line_content in matches:
                all_matches.append((file_path, line_num, line_content))
                if len(all_matches) >= effective_limit:
                    break

        if not all_matches:
            return {
                "content": [{"type": "text", "text": "未找到匹配"}],
                "details": None,
            }

        # 格式化输出
        output_lines: list[str] = []
        file_cache: dict[str, list[str]] = {}
        any_lines_truncated = False

        for file_path, line_number, _ in all_matches:
            # 读取文件内容（使用缓存）
            if file_path not in file_cache:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    file_cache[file_path] = (
                        content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
                    )
                except (OSError, UnicodeDecodeError):
                    file_cache[file_path] = []

            lines = file_cache[file_path]
            if not lines:
                continue

            # 格式化匹配及上下文
            block, was_truncated = _format_match_with_context(
                file_path,
                line_number,
                lines,
                context,
                is_directory,
                search_path,
            )
            if was_truncated:
                any_lines_truncated = True
            output_lines.extend(block)

        # 应用截断
        raw_output = "\n".join(output_lines)
        truncation = truncate_head(raw_output, max_lines=999999)

        output = truncation.content
        details: dict[str, Any] = {}
        notices: list[str] = []

        match_limit_reached = len(all_matches) >= effective_limit

        if match_limit_reached:
            notices.append(
                f"{effective_limit} 匹配限制 reached。使用 limit={effective_limit * 2} 查看更多，或优化模式"
            )
            details["match_limit_reached"] = effective_limit

        if truncation.truncated:
            notices.append(f"{format_size(DEFAULT_MAX_BYTES)} 限制 reached")
            details["truncation"] = truncation

        if any_lines_truncated:
            notices.append(f"部分行被截断到 {GREP_MAX_LINE_LENGTH} 字符。使用 read 工具查看完整行")
            details["lines_truncated"] = True

        if notices:
            output += f"\n\n[{'. '.join(notices)}]"

        return {
            "content": [{"type": "text", "text": output}],
            "details": details if details else None,
        }

    return {
        "name": "grep",
        "label": "grep",
        "description": f"搜索文件内容中的模式。返回匹配的行及其文件路径和行号。遵循 .gitignore。输出被截断到 {DEFAULT_LIMIT} 匹配或 {DEFAULT_MAX_BYTES // 1024}KB（以先达到者为准）。长行被截断到 {GREP_MAX_LINE_LENGTH} 字符。",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "搜索模式（正则或字面字符串）",
                },
                "path": {
                    "type": "string",
                    "description": "要搜索的目录或文件（默认：当前目录）",
                },
                "glob": {
                    "type": "string",
                    "description": "按 glob 模式过滤文件，如 '*.py' 或 '**/*.test.py'",
                },
                "ignoreCase": {
                    "type": "boolean",
                    "description": "不区分大小写搜索（默认：false）",
                },
                "literal": {
                    "type": "boolean",
                    "description": "将模式视为字面字符串而非正则（默认：false）",
                },
                "context": {
                    "type": "integer",
                    "description": "每匹配项前后显示的行数（默认：0）",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回的最大匹配数（默认：100）",
                },
            },
            "required": ["pattern"],
        },
        "execute": execute,
    }


def grep_tool(cwd: str | None = None) -> dict[str, Any]:
    """创建默认 grep 工具（使用当前工作目录）。

    Args:
        cwd: 工作目录，默认为当前目录。

    Returns:
        Grep 工具定义。

    """
    return create_grep_tool(cwd or os.getcwd())
