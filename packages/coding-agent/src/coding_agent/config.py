"""Coding Agent 配置模块。

提供目录路径管理和版本常量。
所有路径都基于用户主目录下的 ~/.pi 目录。
"""

from __future__ import annotations

import os
from pathlib import Path

# ============================================================================
# 版本常量
# ============================================================================

VERSION = "0.1.0"
"""Coding Agent 版本号"""

# ============================================================================
# 路径常量
# ============================================================================

AGENT_DIR_NAME = ".pi/agent"
"""Agent 目录名"""

SESSIONS_DIR_NAME = "sessions"
"""会话子目录名"""

# ============================================================================
# 路径函数
# ============================================================================


def get_agent_dir() -> str:
    """获取 Agent 目录路径

    返回 ~/.pi/agent 目录的绝对路径。
    目录不存在时会自动创建。

    Returns:
        Agent 目录的绝对路径

    Example:
        >>> agent_dir = get_agent_dir()
        >>> print(agent_dir)
        /Users/username/.pi/agent
    """
    home = Path.home()
    agent_dir = home / AGENT_DIR_NAME
    agent_dir.mkdir(parents=True, exist_ok=True)
    return str(agent_dir)


def get_sessions_dir() -> str:
    """获取会话根目录路径

    返回 ~/.pi/agent/sessions 目录的绝对路径。
    目录不存在时会自动创建。

    Returns:
        会话根目录的绝对路径

    Example:
        >>> sessions_dir = get_sessions_dir()
        >>> print(sessions_dir)
        /Users/username/.pi/agent/sessions
    """
    agent_dir = Path(get_agent_dir())
    sessions_dir = agent_dir / SESSIONS_DIR_NAME
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return str(sessions_dir)


def _encode_cwd_for_path(cwd: str) -> str:
    """将工作目录编码为安全的目录名

    将路径中的特殊字符替换为安全的字符，用于创建会话子目录。

    Args:
        cwd: 工作目录路径

    Returns:
        编码后的安全目录名

    Example:
        >>> _encode_cwd_for_path("/home/user/myproject")
        '--home-user-myproject--'
        >>> _encode_cwd_for_path("C:\\Users\\user\\project")
        '--C-Users-user-project--'
    """
    # 移除开头的斜杠或反斜杠
    cleaned = cwd.lstrip("/\\")
    # 将所有路径分隔符和冒号替换为连字符
    encoded = cleaned.replace("/", "-").replace("\\", "-").replace(":", "-")
    # 添加前后缀以确保唯一性
    return f"--{encoded}--"


def get_default_session_dir(cwd: str) -> str:
    """获取默认会话目录路径

    根据工作目录生成唯一的会话子目录路径。
    路径格式: ~/.pi/agent/sessions/--encoded-cwd--/

    Args:
        cwd: 工作目录路径

    Returns:
        会话目录的绝对路径

    Example:
        >>> session_dir = get_default_session_dir("/home/user/myproject")
        >>> print(session_dir)
        /Users/username/.pi/agent/sessions/--home-user-myproject--
    """
    sessions_root = Path(get_sessions_dir())
    encoded = _encode_cwd_for_path(cwd)
    session_dir = sessions_root / encoded
    session_dir.mkdir(parents=True, exist_ok=True)
    return str(session_dir)


# ============================================================================
# 路径验证函数
# ============================================================================


def is_valid_session_file(file_path: str) -> bool:
    """验证文件是否为有效的会话文件

    检查文件是否存在且以有效的会话头部开头。

    Args:
        file_path: 要验证的文件路径

    Returns:
        如果是有效的会话文件返回 True，否则返回 False
    """
    import json

    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if not first_line:
                return False
            header = json.loads(first_line)
            return header.get("type") == "session" and isinstance(header.get("id"), str)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return False


def ensure_dir_exists(dir_path: str) -> str:
    """确保目录存在

    如果目录不存在则创建，包括所有必要的父目录。

    Args:
        dir_path: 目录路径

    Returns:
        目录的绝对路径
    """
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return str(path.absolute())


# ============================================================================
# Pi 文档路径
# ============================================================================


def get_readme_path() -> str:
    """获取 README 文档路径

    Returns:
        README 文档的路径
    """
    return "~/.pi/docs/README.md"


def get_docs_path() -> str:
    """获取文档目录路径

    Returns:
        文档目录的路径
    """
    return "~/.pi/docs"


def get_examples_path() -> str:
    """获取示例目录路径

    Returns:
        示例目录的路径
    """
    return "~/.pi/examples"
