"""
Kimi Provider 实现 - 针对 Kimi API 优化的 Anthropic 兼容层

Kimi API 基于 Anthropic Messages API 设计，本实现继承自 AnthropicProvider，
针对 Kimi 特有功能进行优化：
- 默认使用 Kimi API 地址和模型
- 支持 Kimi 特有的 reasoning 配置
- 针对 Kimi 缓存行为优化

使用方式：
    export KIMI_API_KEY=your-api-key

    provider = KimiProvider(model="kimi-k2-turbo-preview")
    provider = provider.with_thinking("medium")

    stream = provider.stream(model, context)
    async for event in stream:
        if event.type == "thinking_delta":
            print(f"[思考] {event.delta}", end="")
        elif event.type == "text_delta":
            print(event.delta, end="")
"""

from __future__ import annotations

import copy
import os
from typing import Any, ClassVar, Literal

from ai.providers.anthropic import AnthropicProvider
from ai.types import Model, ModelCapabilities, ModelCost, ThinkingLevel


class KimiProvider(AnthropicProvider):
    """Kimi Provider - 优化 Kimi API 访问

    Kimi API 与 Anthropic Messages API 高度兼容，本 Provider：
    1. 默认使用 Kimi API 地址 (https://api.moonshot.cn)
    2. 优先从 KIMI_API_KEY 环境变量读取 API 密钥
    3. 针对 Kimi 模型优化 thinking/reasoning 配置
    4. 提供常用 Kimi 模型的预设配置

    示例：
        provider = KimiProvider(model="kimi-k2-turbo-preview")

        # 启用 reasoning
        provider = provider.with_thinking("medium")

        # 流式生成
        stream = provider.stream(model, context)
        async for event in stream:
            match event.type:
                case "thinking_delta":
                    print(f"[思考] {event.delta}", end="")
                case "text_delta":
                    print(event.delta, end="")
    """

    name: str = "kimi"

    # Kimi 支持的模型配置
    # 参考：https://platform.moonshot.cn/docs
    SUPPORTED_MODELS: ClassVar[dict[str, dict[str, Any]]] = {
        "kimi-k2-turbo-preview": {
            "name": "Kimi K2 Turbo",
            "context_window": 256000,
            "max_tokens": 16384,
            "supports_reasoning": True,
            "supports_thinking": True,
        },
        "kimi-k2": {
            "name": "Kimi K2",
            "context_window": 256000,
            "max_tokens": 16384,
            "supports_reasoning": True,
            "supports_thinking": True,
        },
    }

    def __init__(
        self,
        *,
        model: str = "kimi-k2-turbo-preview",
        api_key: str | None = None,
        base_url: str = "https://api.moonshot.cn",
        default_max_tokens: int = 8192,
    ) -> None:
        """初始化 KimiProvider

        Args:
            model: 模型名称，默认 "kimi-k2-turbo-preview"
            api_key: API 密钥，默认从 KIMI_API_KEY 或 API_KEY 环境变量读取
            base_url: API 基础 URL，默认 https://api.moonshot.cn
            default_max_tokens: 默认最大生成 token 数
        """
        # 先调用基类初始化（无参数版本）
        super().__init__()

        # 保存配置
        self._model = model
        self._api_key = api_key or os.environ.get("KIMI_API_KEY") or os.environ.get("API_KEY")
        self._base_url = base_url
        self._default_max_tokens = default_max_tokens
        # 生成参数字典
        self._generation_kwargs: dict[str, Any] = {}

    def with_thinking(self, effort: ThinkingLevel | Literal["off"]) -> "KimiProvider":
        """配置 reasoning/thinking 模式

        Kimi K2 系列模型支持 reasoning 功能，通过 budget_tokens 控制思考强度：
        - "off": 禁用 reasoning
        - "minimal": 轻量级推理（512 tokens）
        - "low": 基础推理（1024 tokens）
        - "medium": 标准推理（4096 tokens）
        - "high": 深度推理（16000 tokens）
        - "xhigh": 极致推理（32000 tokens）

        Args:
            effort: 思考强度等级

        Returns:
            新的 KimiProvider 实例（不可变更新）

        示例：
            provider = KimiProvider()
            provider = provider.with_thinking("medium")
        """
        new_self = copy.copy(self)

        # Kimi 的 thinking budget 映射
        budgets: dict[ThinkingLevel | Literal["off"], int | None] = {
            "off": None,
            "minimal": 512,
            "low": 1024,
            "medium": 4096,
            "high": 16000,
            "xhigh": 32000,
        }

        budget = budgets.get(effort)

        if budget is None:
            thinking_config: dict[str, Any] = {"type": "disabled"}
        else:
            thinking_config = {"type": "enabled", "budget_tokens": budget}

        # 深拷贝 generation_kwargs
        new_self._generation_kwargs = copy.deepcopy(self._generation_kwargs)
        new_self._generation_kwargs["thinking"] = thinking_config

        return new_self

    def with_generation_kwargs(self, **kwargs: Any) -> "KimiProvider":
        """更新生成参数

        创建一个新的 provider 实例，更新生成参数。

        Args:
            **kwargs: 生成参数，如 temperature, max_tokens, thinking 等

        Returns:
            新的 KimiProvider 实例
        """
        new_self = copy.copy(self)

        # 深拷贝避免修改原实例
        new_self._generation_kwargs = copy.deepcopy(self._generation_kwargs)
        new_self._generation_kwargs.update(kwargs)

        return new_self

    def get_model(self, model_id: str | None = None) -> Model:
        """获取模型配置

        Args:
            model_id: 模型 ID，默认使用初始化时指定的模型

        Returns:
            Model 配置对象

        Raises:
            ValueError: 如果模型 ID 不受支持
        """
        resolved_id = model_id or self._model

        if resolved_id in self.SUPPORTED_MODELS:
            config = self.SUPPORTED_MODELS[resolved_id]
            return Model(
                id=resolved_id,
                name=config["name"],
                api="anthropic-messages",
                provider="kimi",
                base_url=self._base_url,
                capabilities=ModelCapabilities(
                    reasoning=config.get("supports_reasoning", False),
                    input=["text", "image"],
                ),
                cost=config.get(
                    "cost",
                    ModelCost(input=0, output=0, cache_read=0, cache_write=0),
                ),
                context_window=config["context_window"],
                max_tokens=config["max_tokens"],
            )

        # 对于未知模型，返回通用配置
        return Model(
            id=resolved_id,
            name=resolved_id,
            api="anthropic-messages",
            provider="kimi",
            base_url=self._base_url,
            capabilities=ModelCapabilities(reasoning=False, input=["text"]),
            cost=ModelCost(input=0, output=0, cache_read=0, cache_write=0),
            context_window=128000,
            max_tokens=self._default_max_tokens,
        )

    @property
    def models(self) -> list[Model]:
        """返回支持的模型列表"""
        return [self.get_model(model_id) for model_id in self.SUPPORTED_MODELS.keys()]

    @property
    def thinking_effort(self) -> ThinkingLevel | Literal["off"] | None:
        """获取当前 thinking 配置等级

        Returns:
            当前的 thinking 等级，如果未配置则返回 None
        """
        thinking_config = self._generation_kwargs.get("thinking")
        if not thinking_config:
            return None

        if thinking_config.get("type") == "disabled":
            return "off"

        budget = thinking_config.get("budget_tokens", 0)
        if budget is None:
            return "off"
        if budget <= 512:
            return "minimal"
        elif budget <= 1024:
            return "low"
        elif budget <= 4096:
            return "medium"
        elif budget <= 16000:
            return "high"
        else:
            return "xhigh"

    def _get_model(self) -> str:
        """获取当前模型 ID"""
        return self._model

    def _get_base_url(self) -> str:
        """获取 API 基础 URL"""
        return self._base_url

    def _get_api_key(self) -> str | None:
        """获取 API 密钥"""
        return self._api_key

    def _get_default_max_tokens(self) -> int:
        """获取默认最大生成 token 数"""
        return self._default_max_tokens

    def _get_generation_kwargs(self) -> dict[str, Any]:
        """获取生成参数

        Returns:
            生成参数字典
        """
        kwargs: dict[str, Any] = {
            "max_tokens": self._default_max_tokens,
        }
        kwargs.update(self._generation_kwargs)
        return kwargs
