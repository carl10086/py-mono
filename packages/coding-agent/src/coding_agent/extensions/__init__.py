"""扩展系统模块。

提供插件化扩展机制。
"""

from __future__ import annotations

from .loader import (
    discover_extensions,
    load_extension,
    load_extensions,
)
from .runner import ExtensionRunner
from .types import (
    Extension,
    ExtensionContext,
    ToolDefinition,
)
from .wrapper import (
    clear_registered_tools,
    get_wrapped_tools,
    register_tool,
    unregister_tool,
    wrap_registered_tool,
    wrap_registered_tools,
)

__all__ = [
    "Extension",
    "ExtensionContext",
    "ExtensionRunner",
    "ToolDefinition",
    "clear_registered_tools",
    "discover_extensions",
    "get_wrapped_tools",
    "load_extension",
    "load_extensions",
    "register_tool",
    "unregister_tool",
    "wrap_registered_tool",
    "wrap_registered_tools",
]
