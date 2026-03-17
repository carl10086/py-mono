"""
示例 01: 基础对话

SDK 自动从环境变量读取配置：
- API_KEY 或 ANTHROPIC_API_KEY: API 密钥
- BASE_URL 或 ANTHROPIC_BASE_URL: 自定义 API 地址（可选）

运行：
    uv run python examples/basic_chat.py
"""

from __future__ import annotations

import asyncio

from ai.providers.anthropic import AnthropicProvider
from ai.types import Context, Model, ModelCapabilities, ModelCost, UserMessage


async def main():
    print("=" * 60)
    print("示例 01: 基础对话")
    print("=" * 60)

    # 创建模型配置
    # base_url 不传，SDK 自动使用环境变量或 Anthropic 官方地址
    model = Model(
        id="claude-3-5-sonnet-20241022",
        name="Claude 3.5 Sonnet",
        api="anthropic-messages",
        provider="anthropic",
        capabilities=ModelCapabilities(input=["text"]),
        cost=ModelCost(input=0, output=0, cache_read=0, cache_write=0),
        context_window=128000,
        max_tokens=8192,
    )

    print(f"\n模型: {model.name} ({model.id})")
    print(f"API: {model.api}")

    # 构建对话上下文
    context = Context(
        messages=[
            UserMessage(text="你好，请用一句话介绍自己"),
        ],
    )
    print(f"\n用户: {context.messages[0].content}")

    # 创建 provider 并调用
    provider = AnthropicProvider()
    print("\n发送请求...")

    try:
        response = await provider.complete(model=model, context=context)

        # 打印结果
        print("\n" + "=" * 60)
        print("助手响应:")
        print("=" * 60)

        for content in response.content:
            if hasattr(content, "text"):
                print(content.text)

        print("\n" + "=" * 60)
        print("元数据:")
        print("=" * 60)
        print(f"Model: {response.model}")
        print(f"Stop Reason: {response.stop_reason}")
        if response.error_message:
            print(f"Error: {response.error_message}")

        if response.usage:
            print(f"\nTokens: {response.usage.total_tokens}")

    except Exception as e:
        print(f"\n错误: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
