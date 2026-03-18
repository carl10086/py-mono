"""
调试脚本：展示 Thinking 事件的原始流
"""

from __future__ import annotations

import asyncio

from ai.providers import KimiProvider
from ai.types import Context, UserMessage


async def main():
    print("=" * 60)
    print("调试: Thinking 事件流")
    print("=" * 60)

    provider = KimiProvider().with_thinking("low")  # 使用 low 节省 token
    model = provider.get_model()

    context = Context(
        messages=[
            UserMessage(text="计算 15 + 27 = ? 请展示思考过程"),
        ],
    )

    print("\n发送请求，观察事件流...\n")
    print("-" * 60)

    stream = provider.stream(model=model, context=context)

    event_count = 0
    thinking_content = ""
    text_content = ""

    async for event in stream:
        event_count += 1
        print(f"[{event_count}] 事件类型: {event.type}")

        if event.type == "thinking_start":
            print(f"    思考块索引: {event.content_index}")

        elif event.type == "thinking_delta":
            print(f"    增量内容: {repr(event.delta)}")
            thinking_content += event.delta

        elif event.type == "thinking_end":
            print(f"    思考结束，总长度: {len(thinking_content)}")

        elif event.type == "text_start":
            print(f"    文本块索引: {event.content_index}")

        elif event.type == "text_delta":
            # 只打印前 50 字符避免刷屏
            preview = event.delta[:50] + "..." if len(event.delta) > 50 else event.delta
            print(f"    增量内容: {repr(preview)}")
            text_content += event.delta

        elif event.type == "text_end":
            print(f"    文本结束，总长度: {len(text_content)}")

        elif event.type == "done":
            print(f"    流结束，原因: {event.reason}")

        elif event.type == "error":
            print(f"    错误: {event.error}")

    print("-" * 60)
    print(f"\n总共收到 {event_count} 个事件")
    print(f"\n思考内容 ({len(thinking_content)} 字符):")
    print(thinking_content[:200] + "..." if len(thinking_content) > 200 else thinking_content)
    print(f"\n文本内容 ({len(text_content)} 字符):")
    print(text_content[:200] + "..." if len(text_content) > 200 else text_content)


if __name__ == "__main__":
    asyncio.run(main())
