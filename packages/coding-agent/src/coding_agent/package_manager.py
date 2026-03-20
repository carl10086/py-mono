"""包管理器 - 包依赖管理接口

提供包管理的抽象接口和默认实现。
"""

from __future__ import annotations

import logging
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)


# ============================================================================
# 包类型定义
# ============================================================================


@dataclass
class PackageInfo:
    """包信息。

    属性：
        name: 包名称
        version: 版本号
        installed: 是否已安装
        latest_version: 最新版本
        description: 包描述
    """

    name: str
    version: str
    installed: bool
    latest_version: str | None
    description: str


# ============================================================================
# 包管理器接口
# ============================================================================


class PackageManager(ABC):
    """包管理器接口。

    所有包管理器必须实现此接口。
    """

    @abstractmethod
    def install(
        self,
        package_name: str,
        version: str | None = None,
    ) -> bool:
        """安装包。

        Args:
            package_name: 包名称
            version: 版本号（可选）

        Returns:
            是否安装成功
        """
        ...

    @abstractmethod
    def uninstall(self, package_name: str) -> bool:
        """卸载包。

        Args:
            package_name: 包名称

        Returns:
            是否卸载成功
        """
        ...

    @abstractmethod
    def update(self, package_name: str) -> bool:
        """更新包。

        Args:
            package_name: 包名称

        Returns:
            是否更新成功
        """
        ...

    @abstractmethod
    def list_installed(self) -> list[PackageInfo]:
        """列出已安装的包。

        Returns:
            包信息列表
        """
        ...

    @abstractmethod
    def get_info(self, package_name: str) -> PackageInfo | None:
        """获取包信息。

        Args:
            package_name: 包名称

        Returns:
            包信息或 None
        """
        ...

    @abstractmethod
    def search(
        self,
        query: str,
    ) -> list[PackageInfo]:
        """搜索包。

        Args:
            query: 搜索关键词

        Returns:
            匹配的包列表
        """
        ...


# ============================================================================
# 默认包管理器实现
# ============================================================================


class DefaultPackageManager(PackageManager):
    """默认包管理器。

    使用 pip 进行 Python 包管理。

    属性：
        python_path: Python 解释器路径
    """

    def __init__(
        self,
        python_path: str = "python",
    ) -> None:
        """初始化包管理器。

        Args:
            python_path: Python 解释器路径
        """
        self.python_path = python_path

    def _run_pip(
        self,
        args: list[str],
    ) -> tuple[bool, str]:
        """运行 pip 命令。

        Args:
            args: pip 参数列表

        Returns:
            (是否成功, 输出文本)
        """
        cmd = [self.python_path, "-m", "pip"] + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            return success, output
        except Exception as e:
            logger.error(f"pip 命令失败: {e}")
            return False, str(e)

    def install(
        self,
        package_name: str,
        version: str | None = None,
    ) -> bool:
        """安装包。

        Args:
            package_name: 包名称
            version: 版本号（可选）

        Returns:
            是否安装成功
        """
        spec = f"{package_name}=={version}" if version else package_name
        success, output = self._run_pip(["install", spec])

        if success:
            logger.info(f"安装成功: {spec}")
        else:
            logger.error(f"安装失败: {spec}\n{output}")

        return success

    def uninstall(self, package_name: str) -> bool:
        """卸载包。

        Args:
            package_name: 包名称

        Returns:
            是否卸载成功
        """
        success, output = self._run_pip(["uninstall", "-y", package_name])

        if success:
            logger.info(f"卸载成功: {package_name}")
        else:
            logger.error(f"卸载失败: {package_name}\n{output}")

        return success

    def update(self, package_name: str) -> bool:
        """更新包。

        Args:
            package_name: 包名称

        Returns:
            是否更新成功
        """
        success, output = self._run_pip(["install", "--upgrade", package_name])

        if success:
            logger.info(f"更新成功: {package_name}")
        else:
            logger.error(f"更新失败: {package_name}\n{output}")

        return success

    def list_installed(self) -> list[PackageInfo]:
        """列出已安装的包。

        Returns:
            包信息列表
        """
        success, output = self._run_pip(["list", "--format=json"])

        if not success:
            return []

        import json

        try:
            packages = json.loads(output)
            return [
                PackageInfo(
                    name=p["name"],
                    version=p["version"],
                    installed=True,
                    latest_version=None,
                    description="",
                )
                for p in packages
            ]
        except json.JSONDecodeError:
            return []

    def get_info(self, package_name: str) -> PackageInfo | None:
        """获取包信息。

        Args:
            package_name: 包名称

        Returns:
            包信息或 None
        """
        success, output = self._run_pip(["show", package_name])

        if not success:
            return None

        # 解析 pip show 输出
        info: dict[str, str] = {}
        for line in output.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip().lower()] = value.strip()

        return PackageInfo(
            name=info.get("name", package_name),
            version=info.get("version", "unknown"),
            installed=True,
            latest_version=None,
            description=info.get("summary", ""),
        )

    def search(
        self,
        query: str,
    ) -> list[PackageInfo]:
        """搜索包。

        注意：pip search 已被禁用，这里提供一个简化实现。

        Args:
            query: 搜索关键词

        Returns:
            匹配的包列表
        """
        # pip search 已被 PyPI 禁用
        # 返回空列表或实现自定义搜索逻辑
        logger.warning("pip search 已被禁用，无法搜索包")
        return []


# ============================================================================
# No-op 包管理器
# ============================================================================


class NoOpPackageManager(PackageManager):
    """空操作包管理器。

    不执行任何操作，用于禁用包管理功能。
    """

    def install(
        self,
        package_name: str,
        version: str | None = None,
    ) -> bool:
        """安装包（无操作）。"""
        logger.warning(f"包管理已禁用，无法安装: {package_name}")
        return False

    def uninstall(self, package_name: str) -> bool:
        """卸载包（无操作）。"""
        logger.warning(f"包管理已禁用，无法卸载: {package_name}")
        return False

    def update(self, package_name: str) -> bool:
        """更新包（无操作）。"""
        logger.warning(f"包管理已禁用，无法更新: {package_name}")
        return False

    def list_installed(self) -> list[PackageInfo]:
        """列出已安装的包（返回空）。"""
        return []

    def get_info(self, package_name: str) -> PackageInfo | None:
        """获取包信息（返回 None）。"""
        return None

    def search(
        self,
        query: str,
    ) -> list[PackageInfo]:
        """搜索包（返回空）。"""
        return []
