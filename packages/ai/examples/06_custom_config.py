"""
示例 06: 自定义配置与 Provider

学习目标：
- 自定义 base_url 和 api_key
- 使用不同的 Provider
- 环境变量的作用

运行：
    # 使用默认配置（从环境变量读取）
    uv run python examples/06_custom_config.py

    # 使用自定义配置
    export KIMI_BASE_URL=https://api.moonshot.ai/v1
    export KIMI_API_KEY=your-kimi-key
    uv run python examples/06_custom_config.py
"""

from __future__ import annotations

import asyncio
import os

from ai.providers import KimiProvider
from ai.types import Context, UserMessage


async def main():
    print("=" * 60)
    print("示例 06: 自定义配置与 Provider")
    print("=" * 60)

    # 检查环境变量
    api_key = os.environ.get("KIMI_API_KEY") or os.environ.get("API_KEY")
    base_url = os.environ.get("KIMI_BASE_URL") or os.environ.get("BASE_URL")

    print(f"\n环境变量检查:")
    print(f"  KIMI_API_KEY: {'已设置' if api_key else '未设置（将使用 SDK 默认值）'}")
    print(f"  KIMI_BASE_URL: {base_url or '未设置（将使用 Kimi 官方地址）'}")

    context = Context(
        messages=[UserMessage(text="请用一句话介绍自己。")],
    )

    # 方式 1: 完全使用环境变量（不传任何参数）
    print("\n" + "=" * 60)
    print("方式 1: 环境变量配置")
    print("=" * 60)

    try:
        provider_env = KimiProvider()
        model_env = provider_env.get_model()
        response = await provider_env.complete(model=model_env, context=context)
        text = response.content[0].text if response.content else "无回复"
        print(f"回复: {text}")
        print(f"模型: {response.model}")
    except Exception as e:
        print(f"错误: {e}")

    # 方式 2: 显式设置配置
    print("\n" + "=" * 60)
    print("方式 2: 显式配置")
    print("=" * 60)

    try:
        provider_explicit = KimiProvider(
            model="kimi-k2-turbo-preview",
            base_url="https://api.moonshot.ai/v1",
        )
        model_explicit = provider_explicit.get_model()
        response = await provider_explicit.complete(model=model_explicit, context=context)
        text = response.content[0].text if response.content else "无回复"
        print(f"回复: {text[:100]}...")
    except Exception as e:
        print(f"错误: {e}")

    print("\n" + "=" * 60)
    print("配置演示完成")
    print("=" * 60)
    print("\n提示:")
    print("- SDK 优先读取 KIMI_API_KEY/API_KEY 环境变量")
    print("- base_url 可以覆盖默认地址")
    print("- KimiProvider 支持 thinking 模式和 cache key")


if __name__ == "__main__":
    asyncio.run(main())
