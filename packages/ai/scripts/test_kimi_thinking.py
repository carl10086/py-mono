"""
测试脚本：验证 Anthropic SDK 是否能开启 Kimi thinking

运行:
    cd packages/ai && uv run python scripts/test_kimi_thinking.py
"""

import asyncio
import os
from anthropic import AsyncAnthropic


async def test_thinking():
    """测试 Anthropic SDK 调用 Kimi API 的 thinking 功能"""

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.moonshot.cn")

    print("=" * 60)
    print("测试: Anthropic SDK + Kimi thinking")
    print("=" * 60)
    print(f"\nBase URL: {base_url}")
    print(f"API Key: {api_key[:20]}..." if api_key else "未设置")

    client = AsyncAnthropic(api_key=api_key, base_url=base_url)

    # 测试 1: 普通请求（无 thinking）
    print("\n" + "=" * 60)
    print("测试 1: 普通请求")
    print("=" * 60)

    try:
        response = await client.messages.create(
            model="kimi-k2-turbo-preview",
            max_tokens=100,
            messages=[{"role": "user", "content": "计算 123 + 456 = ?"}],
        )
        print(f"✓ 成功!")
        print(f"响应: {response.content[0].text[:100]}")
        print(f"内容类型: {[c.type for c in response.content]}")
    except Exception as e:
        print(f"❌ 失败: {e}")

    # 测试 2: 尝试通过 extra_body 开启 thinking
    print("\n" + "=" * 60)
    print("测试 2: 通过 extra_body 开启 thinking")
    print("=" * 60)

    try:
        # Anthropic SDK 的 create 方法支持 extra_body 参数
        response = await client.messages.create(
            model="kimi-k2-turbo-preview",
            max_tokens=500,
            messages=[{"role": "user", "content": "解方程 2x + 5 = 13，展示思考过程"}],
            extra_body={
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": 1024,
                }
            },
        )
        print(f"✓ 成功!")
        print(f"内容块数: {len(response.content)}")
        for i, content in enumerate(response.content):
            print(f"  [{i}] 类型: {content.type}")
            if content.type == "text":
                print(f"      内容: {content.text[:100]}...")
            elif content.type == "thinking":
                print(f"      思考: {content.thinking[:100]}...")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback

        traceback.print_exc()

    # 测试 3: 流式请求 + thinking
    print("\n" + "=" * 60)
    print("测试 3: 流式请求 + thinking")
    print("=" * 60)

    try:
        has_thinking = False
        has_text = False

        async with client.messages.stream(
            model="kimi-k2-turbo-preview",
            max_tokens=500,
            messages=[{"role": "user", "content": "计算 100 + 200 * 3 = ?"}],
            extra_body={
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": 1024,
                }
            },
        ) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    print(f"  [开始块] 类型: {event.content_block.type}")
                    if event.content_block.type == "thinking":
                        has_thinking = True
                elif event.type == "content_block_delta":
                    if event.delta.type == "thinking_delta":
                        has_thinking = True
                        print(f"  [思考] {event.delta.thinking}", end="", flush=True)
                    elif event.delta.type == "text_delta":
                        has_text = True
                        print(f"  [文本] {event.delta.text}", end="", flush=True)
                elif event.type == "content_block_stop":
                    print(f"\n  [结束块]")

        print(f"\n\n结果:")
        print(f"  有 thinking: {has_thinking}")
        print(f"  有 text: {has_text}")

        if not has_thinking:
            print("\n⚠ 未检测到 thinking 事件")
            print("可能原因:")
            print("1. 当前 API 端点不支持 thinking")
            print("2. 需要特定的模型版本")
            print("3. 需要特定的 API Key 权限")

    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_thinking())
