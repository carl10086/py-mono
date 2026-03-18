"""
示例 02: 流式生成

学习目标：
- 使用 StreamWatcher 简化流式事件处理
- 实时显示生成内容

运行：
    uv run python examples/02_streaming_chat.py
"""

from __future__ import annotations

import asyncio

from ai import StreamWatcher
from ai.providers import KimiProvider
from ai.types import Context, UserMessage


async def main():
    print("=" * 60)
    print("示例 02: 流式生成")
    print("=" * 60)

    provider = KimiProvider()
    model = provider.get_model()

    context = Context(
        messages=[
            UserMessage(text="请用中文写一段 200 字的自我介绍，描述你的能力和特点。"),
        ],
    )

    print(f"\n用户: {context.messages[0].content}")
    print("\n助手: ", end="", flush=True)

    try:
        stream = provider.stream(model=model, context=context)

        # 使用 StreamWatcher 自动处理所有事件
        message = await StreamWatcher().watch(stream)

        print("\n" + "=" * 60)
        print("流式生成完成")
        print("=" * 60)
        print(f"总 Token 数: {message.usage.total_tokens}")
        print(f"停止原因: {message.stop_reason}")

    except Exception as e:
        print(f"\n错误: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
