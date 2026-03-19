"""路径与文件工具。

提供路径规范化、安全检查和验证功能。
"""

from __future__ import annotations

import os
from typing import Final

__all__ = [
    "normalize_path",
    "is_path_inside",
    "validate_path",
]

# 分隔符常量
_SEP: Final[str] = os.sep


def normalize_path(file_path: str) -> str:
    """规范化路径字符串。

    功能：
    1. 去除首尾空白字符。
    2. 扩展用户主目录 (~)。
    3. 去除 @ 前缀。

    Args:
        file_path: 原始路径字符串。

    Returns:
        规范化后的路径字符串。

    """
    trimmed = file_path.strip()

    # 处理 @ 前缀
    if trimmed.startswith("@"):
        trimmed = trimmed[1:]

    # 扩展 ~ 到用户主目录
    if trimmed == "~":
        return os.path.expanduser("~")
    if trimmed.startswith("~/"):
        return os.path.expanduser("~") + trimmed[1:]
    if trimmed.startswith("~"):
        return os.path.expanduser("~") + trimmed[1:]

    return trimmed


def resolve_to_cwd(file_path: str, cwd: str) -> str:
    """将路径解析为相对于工作目录的绝对路径。

    功能：
    1. 先进行路径规范化（normalize_path）。
    2. 如果已经是绝对路径则直接返回。
    3. 否则相对于 cwd 解析。

    Args:
        file_path: 文件路径（相对或绝对）。
        cwd: 当前工作目录。

    Returns:
        绝对路径。

    """
    expanded = normalize_path(file_path)

    if os.path.isabs(expanded):
        return expanded

    return os.path.normpath(os.path.join(cwd, expanded))


def is_path_inside(target: str, root: str) -> bool:
    """检查目标路径是否在根路径内（用于安全验证）。

    防止路径遍历攻击，确保目标路径不会超出根目录。

    Args:
        target: 目标路径（应为绝对路径）。
        root: 根路径（应为绝对路径）。

    Returns:
        如果目标路径在根路径内或等于根路径，返回 True。

    """
    # 规范化两个路径
    normalized_target = os.path.normpath(os.path.abspath(target))
    normalized_root = os.path.normpath(os.path.abspath(root))

    # 如果目标等于根路径，返回 True
    if normalized_target == normalized_root:
        return True

    # 确保根路径以分隔符结尾，避免前缀误判
    # 例如 /foo 不应该匹配 /foobar
    if not normalized_root.endswith(_SEP):
        prefix = normalized_root + _SEP
    else:
        prefix = normalized_root

    return normalized_target.startswith(prefix)


def validate_path(
    file_path: str,
    cwd: str,
    require_exists: bool = False,
    allowed_roots: list[str] | None = None,
) -> str:
    """验证路径的有效性和安全性。

    功能：
    1. 路径规范化。
    2. 解析为绝对路径。
    3. 如果 require_exists=True，检查文件是否存在。
    4. 如果提供 allowed_roots，检查路径是否在允许范围内。

    Args:
        file_path: 文件路径。
        cwd: 当前工作目录。
        require_exists: 是否要求文件必须存在。
        allowed_roots: 允许的根路径列表（安全沙箱）。

    Returns:
        验证通过的绝对路径。

    Raises:
        ValueError: 路径验证失败。
        FileNotFoundError: 文件不存在（当 require_exists=True 时）。
        PermissionError: 路径超出允许范围。

    """
    # 解析为绝对路径
    absolute_path = resolve_to_cwd(file_path, cwd)

    # 检查文件是否存在（如果需要）
    if require_exists and not os.path.exists(absolute_path):
        raise FileNotFoundError(f"路径不存在: {file_path}")

    # 检查是否在允许范围内
    if allowed_roots is not None:
        is_allowed = any(is_path_inside(absolute_path, root) for root in allowed_roots)
        if not is_allowed:
            raise PermissionError(f"路径超出允许范围: {file_path}")

    return absolute_path
