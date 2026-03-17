"""
示例 08: 思考模式与推理过程

学习目标：
- 启用思考/推理模式
- 接收 ThinkingContent
- 观察推理过程

运行：
    uv run python examples/08_thinking_mode.py

注意：
    思考模式需要模型支持（Kimi K2 支持）
"""

from __future__ import annotations

import asyncio

from ai.providers import KimiProvider
from ai.types import Context, UserMessage


async def main():
    print("=" * 60)
    print("示例 08: 思考模式与推理过程")
    print("=" * 60)

    provider = KimiProvider()
    provider_thinking = provider.with_thinking("medium")
    model = provider_thinking.get_model()

    print(f"\nThinking 模式: {provider_thinking.thinking_effort}")

    # 需要推理的问题
    context = Context(
        messages=[
            UserMessage(
                text="""一个水箱有两个进水管 A 和 B。
A 管单独注满需要 6 小时，B 管单独注满需要 4 小时。
如果同时打开 A 和 B，需要多久注满？
请详细展示你的思考过程。"""
            ),
        ],
    )

    print(f"\n问题:\n{context.messages[0].content}\n")
    print("=" * 60)
    print("思考过程:")
    print("=" * 60)

    try:
        stream = provider_thinking.stream(model=model, context=context)

        thinking_started = False
        answer_started = False

        async for event in stream:
            if event.type == "thinking_start":
                thinking_started = True
                print("\n🧠 开始思考...")

            elif event.type == "thinking_delta":
                if not thinking_started:
                    thinking_started = True
                    print("\n🧠 思考内容:")
                print(event.delta, end="", flush=True)

            elif event.type == "thinking_end":
                print("\n\n✅ 思考结束")
                print("\n" + "=" * 60)
                print("最终答案:")
                print("=" * 60)

            elif event.type == "text_start":
                if not answer_started:
                    answer_started = True
                    print()

            elif event.type == "text_delta":
                print(event.delta, end="", flush=True)

            elif event.type == "done":
                print("\n")

        # 获取完整结果
        message = await stream.result()

        print("=" * 60)
        print("消息内容分析:")
        print("=" * 60)

        for i, content in enumerate(message.content):
            if content.type == "thinking":
                print(f"\n[{i + 1}] 思考块:")
                print(f"    长度: {len(content.thinking)} 字符")
                print(f"    预览: {content.thinking[:200]}...")
            elif content.type == "text":
                print(f"\n[{i + 1}] 文本块:")
                print(f"    长度: {len(content.text)} 字符")
                print(f"    预览: {content.text[:200]}...")

        print(f"\n总 Token 数: {message.usage.total_tokens}")
        print(f"停止原因: {message.stop_reason}")

    except Exception as e:
        print(f"\n错误: {e}")
        print("\n注意：思考模式需要模型支持。")
        print("Kimi K2 支持 thinking 模式。")

    print("\n" + "=" * 60)
    print("思考模式演示完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
