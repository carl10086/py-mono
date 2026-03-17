"""
示例 09: 多模态输入（图文）

学习目标：
- 发送图像给 AI
- 使用 ImageContent
- base64 编码处理

运行：
    # 需要准备一张图片
    uv run python examples/multimodal.py /path/to/image.png

    # 或使用示例图片
    uv run python examples/multimodal.py
"""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path

from ai.providers.anthropic import AnthropicProvider
from ai.types import (
    Context,
    ImageContent,
    Model,
    ModelCapabilities,
    ModelCost,
    TextContent,
    UserMessage,
)


def encode_image(image_path: str) -> tuple[str, str]:
    """读取并编码图片为 base64"""
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"图片不存在: {image_path}")

    ext = path.suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime_type = mime_types.get(ext, "image/png")

    with open(path, "rb") as f:
        image_data = f.read()

    base64_data = base64.b64encode(image_data).decode("utf-8")

    return base64_data, mime_type


async def main():
    print("=" * 60)
    print("示例 09: 多模态输入（图文）")
    print("=" * 60)

    # 检查是否有示例图片
    example_image = None
    for ext in [".png", ".jpg", ".jpeg"]:
        test_path = Path(f"example_image{ext}")
        if test_path.exists():
            example_image = str(test_path)
            break

    if example_image:
        print(f"\n使用图片: {example_image}")
        image_data, mime_type = encode_image(example_image)
        print(f"图片类型: {mime_type}")
        print(f"数据大小: {len(image_data)} 字符")

        user_content = [
            TextContent(text="这张图片里有什么？请详细描述。"),
            ImageContent(data=image_data, mime_type=mime_type),
        ]
    else:
        print("\n未找到示例图片，使用纯文本演示...")
        print("（你可以准备一张图片放到当前目录，命名为 example_image.png）")
        user_content = "请描述一张美丽的风景图片。"

    model = Model(
        id="claude-3-5-sonnet-20241022",
        name="Claude 3.5 Sonnet",
        api="anthropic-messages",
        provider="anthropic",
        capabilities=ModelCapabilities(input=["text", "image"]),
        cost=ModelCost(input=0, output=0, cache_read=0, cache_write=0),
        context_window=262144,
        max_tokens=4096,
    )

    context = Context(
        messages=[UserMessage(content=user_content)],
    )

    provider = AnthropicProvider()

    print("\n发送请求...")

    try:
        response = await provider.complete(model=model, context=context)

        print("\n" + "=" * 60)
        print("助手回复:")
        print("=" * 60)

        for content in response.content:
            if content.type == "text":
                print(content.text)

        print(f"\n总 Token 数: {response.usage.total_tokens}")

    except Exception as e:
        print(f"\n错误: {e}")

    print("\n" + "=" * 60)
    print("多模态演示完成")
    print("=" * 60)
    print("\n提示:")
    print("- Claude 3.5 Sonnet 支持图像输入")
    print("- 图片需要转为 base64 编码")
    print("- 大图片会消耗较多 token")


if __name__ == "__main__":
    asyncio.run(main())
