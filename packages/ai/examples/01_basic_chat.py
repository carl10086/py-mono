"""
示例 01: 基础对话

使用 KimiProvider 自动从环境变量读取配置：
- KIMI_API_KEY 或 API_KEY: API 密钥

运行：
    uv run python examples/01_basic_chat.py
"""

from __future__ import annotations

import asyncio

from ai.providers import KimiProvider
from ai.types import Context, UserMessage


async def main():
    print("=" * 60)
    print("示例 01: 基础对话")
    print("=" * 60)

    # 创建 provider（自动从环境变量读取配置）
    provider = KimiProvider()
    model = provider.get_model()

    print(f"\n模型: {model.name} ({model.id})")
    print(f"API: {model.api}")

    # 构建对话上下文
    context = Context(
        messages=[
            UserMessage(text="你好，请用一句话介绍自己"),
        ],
    )
    print(f"\n用户: {context.messages[0].content}")

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
