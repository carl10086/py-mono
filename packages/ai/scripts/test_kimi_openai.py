"""
临时测试脚本：验证 OpenAI SDK 调用 Kimi API

运行:
    cd packages/ai && uv run python scripts/test_kimi_openai.py
"""

import asyncio
import os
from openai import AsyncOpenAI


async def test():
    """测试 OpenAI SDK 调用 Kimi API"""

    # 获取 API Key（参考 kimi-cli 的方式）
    api_key = (
        os.environ.get("KIMI_API_KEY")
        or os.environ.get("API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
    )

    if not api_key:
        print("❌ 未找到 API Key")
        print("请设置 KIMI_API_KEY 或 API_KEY 或 ANTHROPIC_API_KEY")
        return

    print(f"✓ API Key: {api_key[:20]}...")

    # 创建客户端（参考 kimi-cli 使用 api.moonshot.ai）
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.moonshot.ai/v1",
    )

    print(f"✓ Base URL: {client.base_url}")
    print(f"✓ Model: kimi-k2-turbo-preview")

    # 测试普通请求
    print("\n" + "=" * 60)
    print("测试 1: 普通对话")
    print("=" * 60)

    try:
        response = await client.chat.completions.create(
            model="kimi-k2-turbo-preview",
            messages=[{"role": "user", "content": "你好，请用一句话介绍自己。"}],
            max_tokens=100,
        )

        print(f"✓ 成功!")
        print(f"响应: {response.choices[0].message.content}")
        print(f"Token: {response.usage.total_tokens if response.usage else 'N/A'}")

    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback

        traceback.print_exc()

    # 测试流式请求
    print("\n" + "=" * 60)
    print("测试 2: 流式对话")
    print("=" * 60)

    try:
        stream = await client.chat.completions.create(
            model="kimi-k2-turbo-preview",
            messages=[{"role": "user", "content": "计算 123 + 456 = ?"}],
            max_tokens=100,
            stream=True,
            stream_options={"include_usage": True},
        )

        print("✓ 流式响应:")
        content = ""
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content
                print(chunk.choices[0].delta.content, end="", flush=True)

        print(f"\n\n✓ 完整内容: {content}")

    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback

        traceback.print_exc()

    # 测试 thinking（如果支持）
    print("\n" + "=" * 60)
    print("测试 3: Thinking 模式")
    print("=" * 60)

    try:
        stream = await client.chat.completions.create(
            model="kimi-k2-turbo-preview",
            messages=[{"role": "user", "content": "解方程 2x + 5 = 13"}],
            max_tokens=500,
            stream=True,
            extra_body={
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": 1024,
                }
            },
        )

        print("✓ Thinking 响应:")
        has_thinking = False
        async for chunk in stream:
            # 检查是否有 reasoning_content
            reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
            if reasoning:
                has_thinking = True
                print(f"[思考] {reasoning}", end="", flush=True)

            if chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)

        if has_thinking:
            print("\n✓ 检测到 thinking 内容!")
        else:
            print("\n⚠ 未检测到 thinking 内容（可能不支持或配置不正确）")

    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test())
