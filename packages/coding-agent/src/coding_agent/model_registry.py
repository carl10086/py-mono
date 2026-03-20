"""模型注册表模块 - 对齐 pi-mono TypeScript 实现（简化版）

管理内置和自定义模型，提供模型发现和 API Key 解析。

简化说明：
- 核心功能：模型列表、可用模型筛选、模型查找
- 移除了复杂的模型配置验证（JSON Schema）
- 移除了动态 Provider 注册
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai.types import Model


# ============================================================================
# 数据类
# ============================================================================


@dataclass
class ModelInfo:
    """模型信息（简化版）"""

    id: str
    name: str
    provider: str
    api: str


# ============================================================================
# 模型注册表
# ============================================================================


class ModelRegistry:
    """模型注册表

    管理可用模型，支持：
    - 获取所有模型
    - 获取有认证的模型
    - 按提供商和 ID 查找模型
    """

    def __init__(self) -> None:
        """初始化模型注册表"""
        self._models: list[ModelInfo] = []
        self._load_builtin_models()

    def _load_builtin_models(self) -> None:
        """加载内置模型列表"""
        # 简化版：添加一些常用模型
        self._models = [
            ModelInfo(
                id="claude-3-opus",
                name="Claude 3 Opus",
                provider="anthropic",
                api="anthropic-messages",
            ),
            ModelInfo(
                id="claude-3-sonnet",
                name="Claude 3 Sonnet",
                provider="anthropic",
                api="anthropic-messages",
            ),
            ModelInfo(id="gpt-4", name="GPT-4", provider="openai", api="openai-completions"),
            ModelInfo(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider="openai",
                api="openai-completions",
            ),
        ]

    def get_all(self) -> list[ModelInfo]:
        """获取所有模型"""
        return self._models[:]

    def get_available(self, has_auth: list[str] | None = None) -> list[ModelInfo]:
        """获取可用模型（有认证的）

        Args:
            has_auth: 有认证的提供商列表

        Returns:
            可用模型列表
        """
        if not has_auth:
            return []
        return [m for m in self._models if m.provider in has_auth]

    def find(self, provider: str, model_id: str) -> ModelInfo | None:
        """查找模型

        Args:
            provider: 提供商名称
            model_id: 模型 ID

        Returns:
            模型信息，如果未找到返回 None
        """
        for model in self._models:
            if model.provider == provider and model.id == model_id:
                return model
        return None

    def cycle_model(
        self,
        current_provider: str,
        current_model: str,
        has_auth: list[str],
    ) -> ModelInfo | None:
        """循环切换到下一个模型

        Args:
            current_provider: 当前提供商
            current_model: 当前模型 ID
            has_auth: 有认证的提供商列表

        Returns:
            下一个模型，如果没有可用模型返回 None
        """
        available = self.get_available(has_auth)
        if not available:
            return None

        # 找到当前模型的索引
        current_idx = -1
        for i, model in enumerate(available):
            if model.provider == current_provider and model.id == current_model:
                current_idx = i
                break

        # 返回下一个模型
        next_idx = (current_idx + 1) % len(available)
        return available[next_idx]


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "ModelInfo",
    "ModelRegistry",
]
