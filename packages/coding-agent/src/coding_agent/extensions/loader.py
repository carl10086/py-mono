"""扩展加载器 - 发现和加载扩展

提供扩展发现和加载功能。
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import Extension

logger: logging.Logger = logging.getLogger(__name__)


def _load_extension_module(file_path: Path) -> type[Extension] | None:
    """从文件加载扩展模块。

    Args:
        file_path: 扩展文件路径

    Returns:
        扩展类或 None
    """
    try:
        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        if spec is None or spec.loader is None:
            logger.warning(f"无法加载扩展文件: {file_path}")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[file_path.stem] = module
        spec.loader.exec_module(module)

        # 查找 Extension 子类
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and attr.__name__ != "Extension" and hasattr(attr, "id"):
                return attr  # type: ignore[return-value]

        logger.warning(f"在 {file_path} 中未找到扩展类")
        return None

    except Exception as e:
        logger.error(f"加载扩展失败 {file_path}: {e}")
        return None


def _scan_directory(directory: Path) -> list[Path]:
    """扫描目录中的扩展文件。

    Args:
        directory: 要扫描的目录

    Returns:
        扩展文件路径列表
    """
    extensions: list[Path] = []

    if not directory.exists():
        return extensions

    for file_path in directory.iterdir():
        if file_path.suffix == ".py" and not file_path.name.startswith("_"):
            extensions.append(file_path)

    return extensions


def discover_extensions(directories: list[Path]) -> list[type[Extension]]:
    """发现扩展。

    Args:
        directories: 要搜索的目录列表

    Returns:
        扩展类列表
    """
    extensions: list[type[Extension]] = []
    seen_ids: set[str] = set()

    for directory in directories:
        for file_path in _scan_directory(directory):
            ext_class = _load_extension_module(file_path)
            if ext_class is not None:
                # 检查重复ID
                if ext_class.id in seen_ids:
                    logger.warning(f"扩展ID重复: {ext_class.id}")
                    continue
                seen_ids.add(ext_class.id)
                extensions.append(ext_class)

    return extensions


def load_extension(
    ext_class: type[Extension],
) -> Extension:
    """实例化扩展。

    Args:
        ext_class: 扩展类

    Returns:
        扩展实例
    """
    return ext_class()


def load_extensions(
    extensions: list[type[Extension]],
) -> list[Extension]:
    """批量加载扩展。

    Args:
        extensions: 扩展类列表

    Returns:
        扩展实例列表
    """
    return [load_extension(ext_class) for ext_class in extensions]
