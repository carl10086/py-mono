"""扩展运行器 - 管理扩展生命周期

提供扩展激活、停用和事件管理功能。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .types import Extension, ExtensionContext

logger: logging.Logger = logging.getLogger(__name__)


class ExtensionRunner:
    """扩展运行器。

    管理扩展的生命周期和事件分发。

    属性：
        context: 扩展上下文
        extensions: 已加载的扩展实例
        commands: 已注册的命令
    """

    def __init__(
        self,
        context: ExtensionContext,
    ) -> None:
        """初始化运行器。

        Args:
            context: 扩展上下文
        """
        self.context: ExtensionContext = context
        self.extensions: dict[str, Extension] = {}
        self.commands: dict[str, Any] = {}

    def activate_extension(self, extension: Extension) -> bool:
        """激活单个扩展。

        Args:
            extension: 扩展实例

        Returns:
            是否激活成功
        """
        if extension.id in self.extensions:
            logger.warning(f"扩展已激活: {extension.id}")
            return False

        try:
            extension.activate(self.context)
            self.extensions[extension.id] = extension
            logger.info(f"扩展已激活: {extension.name} ({extension.id})")
            return True
        except Exception as e:
            logger.error(f"扩展激活失败 {extension.id}: {e}")
            return False

    def deactivate_extension(self, extension_id: str) -> bool:
        """停用扩展。

        Args:
            extension_id: 扩展ID

        Returns:
            是否停用成功
        """
        if extension_id not in self.extensions:
            return False

        extension = self.extensions[extension_id]
        try:
            extension.deactivate()
            del self.extensions[extension_id]
            logger.info(f"扩展已停用: {extension_id}")
            return True
        except Exception as e:
            logger.error(f"扩展停用失败 {extension_id}: {e}")
            return False

    def activate_all(self, extensions: list[Extension]) -> list[str]:
        """批量激活扩展。

        Args:
            extensions: 扩展实例列表

        Returns:
            成功激活的扩展ID列表
        """
        activated: list[str] = []
        for ext in extensions:
            if self.activate_extension(ext):
                activated.append(ext.id)
        return activated

    def deactivate_all(self) -> list[str]:
        """停用所有扩展。

        Returns:
            成功停用的扩展ID列表
        """
        deactivated: list[str] = []
        for ext_id in list(self.extensions.keys()):
            if self.deactivate_extension(ext_id):
                deactivated.append(ext_id)
        return deactivated

    def get_extension(self, extension_id: str) -> Extension | None:
        """获取已激活的扩展。

        Args:
            extension_id: 扩展ID

        Returns:
            扩展实例或 None
        """
        return self.extensions.get(extension_id)

    def get_all_extensions(self) -> list[Extension]:
        """获取所有已激活的扩展。

        Returns:
            扩展实例列表
        """
        return list(self.extensions.values())

    def register_command(
        self,
        name: str,
        handler: Any,
    ) -> None:
        """注册命令。

        Args:
            name: 命令名称
            handler: 命令处理函数
        """
        if name in self.commands:
            logger.warning(f"命令已存在: {name}")
        self.commands[name] = handler

    def unregister_command(self, name: str) -> None:
        """注销命令。

        Args:
            name: 命令名称
        """
        if name in self.commands:
            del self.commands[name]

    def get_command(self, name: str) -> Any | None:
        """获取命令处理函数。

        Args:
            name: 命令名称

        Returns:
            命令处理函数或 None
        """
        return self.commands.get(name)

    def list_commands(self) -> list[str]:
        """获取所有命令名称。

        Returns:
            命令名称列表
        """
        return list(self.commands.keys())

    def get_all_tools(self) -> list[Any]:
        """获取所有扩展的工具。

        Returns:
            工具定义列表
        """
        tools: list[Any] = []
        for ext in self.extensions.values():
            try:
                tools.extend(ext.get_tools())
            except Exception as e:
                logger.error(f"获取扩展 {ext.id} 工具失败: {e}")
        return tools
