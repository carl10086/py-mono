"""
示例 07: 错误处理与优雅降级

学习目标：
- 处理网络错误
- 处理 API 错误
- 使用 EventError
- 优雅的错误恢复

运行：
    # 测试正常情况
    uv run python examples/07_error_handling.py

    # 测试错误情况（使用无效 API key）
    KIMI_API_KEY=invalid_key uv run python examples/07_error_handling.py
"""

from __future__ import annotations

import asyncio
import os

from ai import StreamWatcher
from ai.providers import KimiProvider
from ai.types import Context, UserMessage


async def test_with_error_handling(description: str, context: Context) -> None:
    """带错误处理的测试"""

    print(f"\n{'=' * 60}")
    print(f"测试: {description}")
    print("=" * 60)

    provider = KimiProvider()
    model = provider.get_model()

    try:
        # 方式 1: 使用 complete（同步等待）
        print("\n方式 1: 使用 complete()")
        response = await provider.complete(model=model, context=context)

        if response.stop_reason == "error":
            print(f"❌ 错误: {response.error_message}")
        else:
            text = response.content[0].text if response.content else "无回复"
            print(f"✅ 成功: {text[:100]}...")

    except Exception as e:
        print(f"❌ 异常捕获: {type(e).__name__}: {e}")

    try:
        # 方式 2: 使用 StreamWatcher（流式处理）
        print("\n方式 2: 使用 StreamWatcher")
        stream = provider.stream(model=model, context=context)

        # 使用自定义回调处理错误
        error_message = None

        def on_error(msg: str) -> None:
            nonlocal error_message
            error_message = msg
            print(f"❌ 流错误: {msg}")

        message = await StreamWatcher(
            on_error=on_error,
            on_done=lambda _: None,  # 简化 done 输出
        ).watch(stream)

        if error_message is None:
            print(f"✅ 流结果: {message.stop_reason}")

    except Exception as e:
        print(f"❌ 流异常: {type(e).__name__}: {e}")


async def main():
    print("=" * 60)
    print("示例 07: 错误处理与优雅降级")
    print("=" * 60)

    # 检查当前配置
    api_key = os.environ.get("KIMI_API_KEY") or os.environ.get("API_KEY")
    print(f"\n当前 API_KEY: {'已设置' if api_key else '未设置'}")

    # 测试 1: 正常请求
    context_normal = Context(messages=[UserMessage(text="你好")])
    await test_with_error_handling("正常请求", context_normal)

    # 测试 2: 无效模型 ID
    provider_invalid = KimiProvider(model="invalid-model-id")
    model_invalid = provider_invalid.get_model()
    print(f"\n{'=' * 60}")
    print("测试: 无效模型 ID")
    print("=" * 60)
    print(f"模型 ID: {model_invalid.id}")
    try:
        response = await provider_invalid.complete(model=model_invalid, context=context_normal)
        if response.stop_reason == "error":
            print(f"❌ 错误: {response.error_message}")
        else:
            print(f"✅ 成功（可能使用了默认模型）")
    except Exception as e:
        print(f"❌ 异常: {type(e).__name__}: {e}")

    # 测试 3: 超长消息（可能触发限制）
    long_text = "请重复这句话。" * 5000  # 很长的文本
    context_long = Context(messages=[UserMessage(text=long_text)])
    await test_with_error_handling("超长消息", context_long)

    print("\n" + "=" * 60)
    print("错误处理演示完成")
    print("=" * 60)
    print("\n错误处理要点:")
    print("1. complete() 可能抛出异常，需要用 try-except 包裹")
    print("2. stream() 的错误通过 EventError 事件传递")
    print("3. 检查 response.stop_reason == 'error' 识别错误")
    print("4. 生产环境应实现重试机制和降级策略")


if __name__ == "__main__":
    asyncio.run(main())
