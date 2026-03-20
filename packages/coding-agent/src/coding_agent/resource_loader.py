"""资源加载器 - 统一资源加载接口

提供资源加载的抽象接口和默认实现。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)


# ============================================================================
# 资源加载器接口
# ============================================================================


class ResourceLoader(ABC):
    """资源加载器接口。

    所有资源加载器必须实现此接口。
    """

    @abstractmethod
    def load_text(self, resource_id: str) -> str:
        """加载文本资源。

        Args:
            resource_id: 资源标识符

        Returns:
            文本内容

        Raises:
            ResourceNotFoundError: 资源不存在时
        """
        ...

    @abstractmethod
    def load_json(self, resource_id: str) -> dict[str, Any]:
        """加载 JSON 资源。

        Args:
            resource_id: 资源标识符

        Returns:
            JSON 数据

        Raises:
            ResourceNotFoundError: 资源不存在时
        """
        ...

    @abstractmethod
    def exists(self, resource_id: str) -> bool:
        """检查资源是否存在。

        Args:
            resource_id: 资源标识符

        Returns:
            是否存在
        """
        ...

    @abstractmethod
    def list_resources(self) -> list[str]:
        """列出所有可用资源。

        Returns:
            资源ID列表
        """
        ...


class ResourceNotFoundError(Exception):
    """资源未找到错误。"""

    def __init__(self, resource_id: str) -> None:
        """初始化错误。

        Args:
            resource_id: 资源ID
        """
        self.resource_id = resource_id
        super().__init__(f"资源未找到: {resource_id}")


# ============================================================================
# 默认资源加载器实现
# ============================================================================


class DefaultResourceLoader(ResourceLoader):
    """默认资源加载器。

    从文件系统加载资源。

    属性：
        base_path: 资源基础路径
    """

    def __init__(
        self,
        base_path: Path | str,
    ) -> None:
        """初始化加载器。

        Args:
            base_path: 资源基础路径
        """
        self.base_path = Path(base_path)

    def _resolve_path(self, resource_id: str) -> Path:
        """解析资源路径。

        Args:
            resource_id: 资源标识符

        Returns:
            完整的文件路径
        """
        # 将点号分隔的ID转换为路径
        path_parts = resource_id.replace(".", "/").split("/")
        return self.base_path.joinpath(*path_parts)

    def load_text(self, resource_id: str) -> str:
        """加载文本资源。

        Args:
            resource_id: 资源标识符

        Returns:
            文本内容

        Raises:
            ResourceNotFoundError: 资源不存在
        """
        path = self._resolve_path(resource_id)

        # 尝试多种扩展名
        extensions = ["", ".txt", ".md", ".py", ".json"]

        for ext in extensions:
            full_path = path.with_suffix(ext) if ext else path
            if full_path.exists():
                try:
                    return full_path.read_text(encoding="utf-8")
                except Exception as e:
                    logger.error(f"读取资源失败 {full_path}: {e}")
                    raise ResourceNotFoundError(resource_id) from e

        raise ResourceNotFoundError(resource_id)

    def load_json(self, resource_id: str) -> dict[str, Any]:
        """加载 JSON 资源。

        Args:
            resource_id: 资源标识符

        Returns:
            JSON 数据

        Raises:
            ResourceNotFoundError: 资源不存在
        """
        import json

        path = self._resolve_path(resource_id)

        # 尝试多种扩展名
        extensions = [".json", ""]

        for ext in extensions:
            full_path = path.with_suffix(ext) if ext else path
            if full_path.exists():
                try:
                    text = full_path.read_text(encoding="utf-8")
                    return json.loads(text)
                except Exception as e:
                    logger.error(f"解析JSON失败 {full_path}: {e}")
                    raise ResourceNotFoundError(resource_id) from e

        raise ResourceNotFoundError(resource_id)

    def exists(self, resource_id: str) -> bool:
        """检查资源是否存在。

        Args:
            resource_id: 资源标识符

        Returns:
            是否存在
        """
        path = self._resolve_path(resource_id)

        extensions = ["", ".txt", ".md", ".py", ".json"]

        for ext in extensions:
            full_path = path.with_suffix(ext) if ext else path
            if full_path.exists():
                return True

        return False

    def list_resources(
        self,
        pattern: str = "*",
    ) -> list[str]:
        """列出所有可用资源。

        Args:
            pattern: 文件匹配模式

        Returns:
            资源ID列表
        """
        resources: list[str] = []

        if not self.base_path.exists():
            return resources

        for path in self.base_path.rglob(pattern):
            if path.is_file():
                # 计算相对路径并转换为资源ID
                rel_path = path.relative_to(self.base_path)
                resource_id = str(rel_path.with_suffix("")).replace("/", ".")
                resources.append(resource_id)

        return sorted(resources)


# ============================================================================
# 内存资源加载器
# ============================================================================


class InMemoryResourceLoader(ResourceLoader):
    """内存资源加载器。

    从内存字典中加载资源，用于测试。

    属性：
        resources: 资源字典
    """

    def __init__(
        self,
        resources: dict[str, str] | None = None,
    ) -> None:
        """初始化加载器。

        Args:
            resources: 初始资源字典
        """
        self.resources: dict[str, str] = resources or {}

    def add_resource(
        self,
        resource_id: str,
        content: str,
    ) -> None:
        """添加资源。

        Args:
            resource_id: 资源ID
            content: 资源内容
        """
        self.resources[resource_id] = content

    def load_text(self, resource_id: str) -> str:
        """加载文本资源。

        Args:
            resource_id: 资源标识符

        Returns:
            文本内容

        Raises:
            ResourceNotFoundError: 资源不存在
        """
        if resource_id not in self.resources:
            raise ResourceNotFoundError(resource_id)
        return self.resources[resource_id]

    def load_json(self, resource_id: str) -> dict[str, Any]:
        """加载 JSON 资源。

        Args:
            resource_id: 资源标识符

        Returns:
            JSON 数据
        """
        import json

        text = self.load_text(resource_id)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ResourceNotFoundError(resource_id) from e

    def exists(self, resource_id: str) -> bool:
        """检查资源是否存在。

        Args:
            resource_id: 资源标识符

        Returns:
            是否存在
        """
        return resource_id in self.resources

    def list_resources(self) -> list[str]:
        """列出所有可用资源。

        Returns:
            资源ID列表
        """
        return list(self.resources.keys())
