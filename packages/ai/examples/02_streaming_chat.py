"""
示例 02: 流式生成

学习目标：
- 理解流式事件协议 (AssistantMessageEvent)
- 实时显示生成内容
- 处理不同类型的流事件

运行：
    uv run python examples/02_streaming_chat.py
"""

from __future__ import annotations

import asyncio

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

        # 流式消费事件
        async for event in stream:
            if event.type == "text_start":
                # 文本块开始
                pass
            elif event.type == "text_delta":
                # 文本增量 - 实时输出
                print(event.delta, end="", flush=True)
            elif event.type == "text_end":
                # 文本块结束
                pass
            elif event.type == "done":
                # 流完成
                pass
            elif event.type == "error":
                # 错误
                print(f"\n[错误: {event.error.error_message}]", end="")

        # 获取最终结果
        message = await stream.result()

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
