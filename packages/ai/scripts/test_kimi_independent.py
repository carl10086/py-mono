"""
测试: KimiProvider 独立实现验证。

验证新的独立 KimiProvider 实现。
"""

from __future__ import annotations

import asyncio
import os

from ai.providers import KimiProvider
from ai.types import Context, UserMessage


async def test_thinking() -> None:
    """测试 thinking 功能。"""
    print("=" * 60)
    print("测试: KimiProvider Thinking 功能")
    print("=" * 60)

    provider = KimiProvider()
    provider_thinking = provider.with_thinking("low")

    print(f"\nThinking 配置: {provider_thinking.thinking_effort}")

    context = Context(
        messages=[UserMessage(text="1 + 1 = ? 请展示你的思考过程。")],
    )

    try:
        model = provider_thinking.get_model()
        stream = provider_thinking.stream(model=model, context=context)

        print("\n流式响应:")
        has_thinking = False
        has_text = False

        async for event in stream:
            match event.type:
                case "thinking_start":
                    print("\n🧠 [思考开始]")
                    has_thinking = True
                case "thinking_delta":
                    print(event.delta, end="", flush=True)
                case "thinking_end":
                    print("\n✅ [思考结束]")
                case "text_start":
                    print("\n💬 [回答开始] ", end="")
                    has_text = True
                case "text_delta":
                    print(event.delta, end="", flush=True)
                case "text_end":
                    print("\n✅ [回答结束]")
                case "done":
                    print("\n✅ [流结束]")

        result = await stream.result()
        print(f"\n总 Token: {result.usage.total_tokens}")
        print(f"内容块数: {len(result.content)}")

        for i, content in enumerate(result.content):
            print(f"  [{i}] {content.type}")

        return has_thinking and has_text

    except Exception as e:
        print(f"\n错误: {e}")
        return False


async def test_cache_key() -> None:
    """测试 cache key 配置。"""
    print("\n" + "=" * 60)
    print("测试: Cache Key 配置")
    print("=" * 60)

    provider = KimiProvider()
    provider_cached = provider.with_cache_key("test-session-123")

    # 验证配置已设置（通过检查 _generation_kwargs）
    assert "prompt_cache_key" in provider_cached._generation_kwargs
    assert provider_cached._generation_kwargs["prompt_cache_key"] == "test-session-123"

    print("✅ Cache key 配置正确")
    return True


async def test_model_info() -> None:
    """测试模型信息获取。"""
    print("\n" + "=" * 60)
    print("测试: 模型信息")
    print("=" * 60)

    provider = KimiProvider()
    model = provider.get_model()

    print(f"模型 ID: {model.id}")
    print(f"模型名称: {model.name}")
    print(f"API: {model.api}")
    print(f"Provider: {model.provider}")
    print(f"上下文窗口: {model.context_window}")
    print(f"最大 Token: {model.max_tokens}")
    print(f"支持思考: {model.capabilities.reasoning}")

    assert model.id == "kimi-k2-turbo-preview"
    assert model.api == "openai-chat"
    assert model.provider == "kimi"

    print("✅ 模型信息正确")
    return True


async def main() -> None:
    """运行所有测试。"""
    print("\n" + "=" * 60)
    print("KimiProvider 独立实现测试")
    print("=" * 60)

    # 检查环境
    api_key = os.environ.get("KIMI_API_KEY") or os.environ.get("API_KEY")
    if not api_key:
        print("\n⚠️  未设置 KIMI_API_KEY 或 API_KEY 环境变量")
        print("跳过 API 测试，仅测试基础功能")

    results = []

    # 测试基础功能（不需要 API）
    results.append(("Cache Key", await test_cache_key()))
    results.append(("Model Info", await test_model_info()))

    # 测试 API 功能（需要 API key）
    if api_key:
        results.append(("Thinking", await test_thinking()))
    else:
        print("\n⚠️  跳过 API 测试（需要 API key）")

    # 打印结果
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")

    all_passed = all(passed for _, passed in results)
    print("\n" + ("✅ 所有测试通过" if all_passed else "❌ 部分测试失败"))

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
