"""斜杠命令系统 - 内置命令定义和解析

提供斜杠命令的注册、解析和执行功能。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

logger: logging.Logger = logging.getLogger(__name__)


# ============================================================================
# 命令类型定义
# ============================================================================


@dataclass
class SlashCommand:
    """斜杠命令定义

    属性：
        name: 命令名称（不含斜杠）
        description: 命令描述
        handler: 命令处理函数
        args_help: 参数帮助信息
        hidden: 是否在帮助中隐藏
    """

    name: str
    description: str
    handler: Callable[..., Any]
    args_help: str
    hidden: bool


# ============================================================================
# 命令解析
# ============================================================================


def parse_slash_command(text: str) -> tuple[str, list[str]] | None:
    """解析斜杠命令。

    Args:
        text: 输入文本

    Returns:
        (命令名, 参数列表) 或 None（如果不是命令）
    """
    text = text.strip()

    if not text.startswith("/"):
        return None

    # 移除开头的斜杠
    text = text[1:]

    # 分割命令和参数
    parts = text.split()
    if not parts:
        return None

    command_name = parts[0]
    args = parts[1:]

    return command_name, args


# ============================================================================
# 命令注册表
# ============================================================================


class SlashCommandRegistry:
    """斜杠命令注册表。

    管理所有可用的斜杠命令。
    """

    def __init__(self) -> None:
        """初始化空注册表。"""
        self._commands: dict[str, SlashCommand] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        args_help: str = "",
        hidden: bool = False,
    ) -> None:
        """注册命令。

        Args:
            name: 命令名称
            description: 命令描述
            handler: 处理函数
            args_help: 参数帮助
            hidden: 是否隐藏
        """
        self._commands[name] = SlashCommand(
            name=name,
            description=description,
            handler=handler,
            args_help=args_help,
            hidden=hidden,
        )
        logger.debug(f"注册斜杠命令: /{name}")

    def unregister(self, name: str) -> bool:
        """注销命令。

        Args:
            name: 命令名称

        Returns:
            是否成功注销
        """
        if name in self._commands:
            del self._commands[name]
            return True
        return False

    def get(self, name: str) -> SlashCommand | None:
        """获取命令定义。

        Args:
            name: 命令名称

        Returns:
            命令定义或 None
        """
        return self._commands.get(name)

    def list_commands(self, include_hidden: bool = False) -> list[str]:
        """列出所有命令。

        Args:
            include_hidden: 是否包含隐藏命令

        Returns:
            命令名称列表
        """
        if include_hidden:
            return list(self._commands.keys())
        return [name for name, cmd in self._commands.items() if not cmd.hidden]

    def execute(
        self,
        command_text: str,
        context: Any | None = None,
    ) -> Any:
        """执行命令。

        Args:
            command_text: 命令文本（含斜杠）
            context: 执行上下文

        Returns:
            命令执行结果

        Raises:
            ValueError: 命令不存在
        """
        parsed = parse_slash_command(command_text)
        if parsed is None:
            raise ValueError(f"无效的命令格式: {command_text}")

        name, args = parsed
        cmd = self.get(name)

        if cmd is None:
            raise ValueError(f"未知命令: /{name}")

        logger.debug(f"执行命令: /{name} 参数: {args}")

        try:
            if context is not None:
                return cmd.handler(context, *args)
            return cmd.handler(*args)
        except Exception as e:
            logger.error(f"命令执行失败 /{name}: {e}")
            raise

    def get_help_text(self) -> str:
        """生成帮助文本。

        Returns:
            格式化的帮助文本
        """
        lines: list[str] = []
        lines.append("# 可用斜杠命令")
        lines.append("")

        for name in sorted(self.list_commands()):
            cmd = self._commands[name]
            lines.append(f"**/{name}** {cmd.args_help}")
            lines.append(f"  {cmd.description}")
            lines.append("")

        return "\n".join(lines)


# ============================================================================
# 内置命令
# ============================================================================


def _cmd_help(registry: SlashCommandRegistry) -> str:
    """帮助命令处理函数。"""
    return registry.get_help_text()


def _cmd_clear() -> str:
    """清屏命令。"""
    return "[CLEAR_SCREEN]"


def _cmd_exit() -> str:
    """退出命令。"""
    return "[EXIT]"


def _cmd_model(models: list[str]) -> str:
    """切换模型命令。

    Args:
        models: 模型列表

    Returns:
        切换结果
    """
    if not models:
        return "请指定模型名称"
    return f"切换到模型: {models[0]}"


def _cmd_compact() -> str:
    """压缩命令。"""
    return "[COMPACT_SESSION]"


def _cmd_undo() -> str:
    """撤销命令。"""
    return "[UNDO_LAST]"


def _cmd_redo() -> str:
    """重做命令。"""
    return "[REDO_LAST]"


def create_default_registry() -> SlashCommandRegistry:
    """创建默认命令注册表。

    包含所有内置斜杠命令。

    Returns:
        命令注册表实例
    """
    registry = SlashCommandRegistry()

    # 帮助
    registry.register(
        name="help",
        description="显示帮助信息",
        handler=lambda: _cmd_help(registry),
        args_help="",
    )

    # 清屏
    registry.register(
        name="clear",
        description="清屏",
        handler=_cmd_clear,
        args_help="",
    )

    # 退出
    registry.register(
        name="exit",
        description="退出程序",
        handler=_cmd_exit,
        args_help="",
    )

    # 切换模型
    registry.register(
        name="model",
        description="切换AI模型",
        handler=_cmd_model,
        args_help="[model_name]",
    )

    # 压缩会话
    registry.register(
        name="compact",
        description="压缩会话历史",
        handler=_cmd_compact,
        args_help="",
    )

    # 撤销
    registry.register(
        name="undo",
        description="撤销上一步操作",
        handler=_cmd_undo,
        args_help="",
    )

    # 重做
    registry.register(
        name="redo",
        description="重做上一步操作",
        handler=_cmd_redo,
        args_help="",
    )

    return registry
