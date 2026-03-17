"""
示例 06: 自定义配置与多 Provider

学习目标：
- 自定义 base_url 和 api_key
- 使用不同的 Provider
- 环境变量的作用

运行：
    # 使用默认配置（从环境变量读取）
    uv run python examples/custom_config.py

    # 使用自定义配置
    export BASE_URL=https://api.moonshot.cn
    export API_KEY=your-kimi-key
    uv run python examples/custom_config.py
"""

from __future__ import annotations

import asyncio
import os

from ai.providers.anthropic import AnthropicProvider
from ai.types import Context, Model, ModelCapabilities, ModelCost, UserMessage


async def main():
    print("=" * 60)
    print("示例 06: 自定义配置与多 Provider")
    print("=" * 60)

    # 检查环境变量
    api_key = os.environ.get("API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    base_url = os.environ.get("BASE_URL") or os.environ.get("ANTHROPIC_BASE_URL")

    print(f"\n环境变量检查:")
    print(f"  API_KEY: {'已设置' if api_key else '未设置（将使用 SDK 默认值）'}")
    print(f"  BASE_URL: {base_url or '未设置（将使用 Anthropic 官方地址）'}")

    # 构建模型配置
    # 方式 1: 完全使用环境变量（不传 base_url）
    model_env = Model(
        id="claude-3-5-sonnet-20241022",
        name="Claude via 环境变量",
        api="anthropic-messages",
        provider="anthropic",
        capabilities=ModelCapabilities(input=["text"]),
        cost=ModelCost(input=0, output=0, cache_read=0, cache_write=0),
        context_window=262144,
        max_tokens=2048,
    )

    # 方式 2: 显式设置 base_url
    # 这可以覆盖环境变量或 SDK 默认值
    model_explicit = Model(
        id="claude-3-5-sonnet-20241022",
        name="Claude via 显式配置",
        api="anthropic-messages",
        provider="anthropic",
        base_url="https://api.anthropic.com",  # 显式设置
        capabilities=ModelCapabilities(input=["text"]),
        cost=ModelCost(input=0, output=0, cache_read=0, cache_write=0),
        context_window=262144,
        max_tokens=2048,
    )

    # 方式 3: 使用兼容 API（如 Moonshot）
    model_compatible = None
    if base_url and "moonshot" in base_url:
        model_compatible = Model(
            id="kimi-k2-turbo-preview",
            name="Kimi K2",
            api="anthropic-messages",
            provider="anthropic",
            base_url=base_url,
            capabilities=ModelCapabilities(input=["text"]),
            cost=ModelCost(input=0, output=0, cache_read=0, cache_write=0),
            context_window=128000,
            max_tokens=8192,
        )

    context = Context(
        messages=[UserMessage(text="请用一句话介绍自己。")],
    )

    provider = AnthropicProvider()

    # 测试方式 1
    print("\n" + "=" * 60)
    print("方式 1: 环境变量配置")
    print("=" * 60)

    try:
        response = await provider.complete(model=model_env, context=context)
        text = response.content[0].text if response.content else "无回复"
        print(f"回复: {text}")
        print(f"模型: {response.model}")
    except Exception as e:
        print(f"错误: {e}")

    # 测试方式 2
    print("\n" + "=" * 60)
    print("方式 2: 显式配置")
    print("=" * 60)

    try:
        response = await provider.complete(model=model_explicit, context=context)
        text = response.content[0].text if response.content else "无回复"
        print(f"回复: {text[:100]}...")
    except Exception as e:
        print(f"错误: {e}")

    # 测试方式 3（如果配置了兼容 API）
    if model_compatible:
        print("\n" + "=" * 60)
        print("方式 3: 兼容 API 配置")
        print("=" * 60)

        try:
            response = await provider.complete(model=model_compatible, context=context)
            text = response.content[0].text if response.content else "无回复"
            print(f"回复: {text}")
            print(f"模型: {response.model}")
        except Exception as e:
            print(f"错误: {e}")

    print("\n" + "=" * 60)
    print("配置演示完成")
    print("=" * 60)
    print("\n提示:")
    print("- SDK 优先读取 API_KEY/ANTHROPIC_API_KEY 环境变量")
    print("- base_url 可以覆盖默认地址，支持兼容 API")
    print("- Model.base_url 字段会传递给 SDK 的 base_url 参数")


if __name__ == "__main__":
    asyncio.run(main())
