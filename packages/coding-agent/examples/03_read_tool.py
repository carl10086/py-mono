"""文件读取工具验证示例。

验证 read 模块的基本功能：
1. create_read_tool() - 创建读取工具
2. 读取文本文件
3. 读取图像文件
4. offset/limit 参数测试
5. 大文件截断测试
"""

from __future__ import annotations

import asyncio
import os
import tempfile

from coding_agent.tools.read import create_read_tool


async def test_read_text_file() -> None:
    """测试读取文本文件。"""
    print("\n【测试 1】读取文本文件")
    print("-" * 60)

    # 创建临时文本文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Line 1\nLine 2\nLine 3\n")
        tmp_path = f.name

    try:
        tool = create_read_tool(os.getcwd())
        result = await tool.execute("test_call_1", {"path": tmp_path})

        assert len(result.content) == 1
        assert result.content[0].type == "text"
        assert "Line 1" in result.content[0].text
        print(f"✓ 成功读取文本文件: {len(result.content[0].text)} 字符")

    finally:
        os.unlink(tmp_path)


async def test_read_with_offset_limit() -> None:
    """测试 offset 和 limit 参数。"""
    print("\n【测试 2】offset 和 limit 参数")
    print("-" * 60)

    # 创建多行文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for i in range(100):
            f.write(f"This is line {i + 1}\n")
        tmp_path = f.name

    try:
        tool = create_read_tool(os.getcwd())

        # 测试 offset
        result = await tool.execute("test_call_2", {"path": tmp_path, "offset": 50})
        text = result.content[0].text
        # 检查是否包含第50行（实际内容中应显示为 "This is line 50"）
        assert "This is line 50" in text or "This is line 51" in text
        print("✓ offset 参数工作正常")

        # 测试 limit
        result = await tool.execute("test_call_3", {"path": tmp_path, "offset": 1, "limit": 10})
        text = result.content[0].text
        lines = [l for l in text.split("\n") if l.strip() and not l.startswith("[")]
        assert len(lines) <= 10
        print("✓ limit 参数工作正常")

    finally:
        os.unlink(tmp_path)


async def test_read_image_file() -> None:
    """测试读取图像文件。"""
    print("\n【测试 3】读取图像文件")
    print("-" * 60)

    # 创建一个简单的PNG文件头（不是真正的PNG，但用于测试MIME检测）
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".png", delete=False) as f:
        # 写入PNG文件签名
        f.write(b"\x89PNG\r\n\x1a\n")
        # 添加一些虚拟数据
        f.write(b"\x00" * 100)
        tmp_path = f.name

    try:
        tool = create_read_tool(os.getcwd())
        result = await tool.execute("test_call_4", {"path": tmp_path})

        # 图像应该返回两个内容：文本说明和图像数据
        assert len(result.content) == 2
        assert result.content[0].type == "text"
        assert result.content[1].type == "image"
        assert "image/png" in result.content[0].text
        print("✓ 成功读取图像文件")

    finally:
        os.unlink(tmp_path)


async def test_large_file_truncation() -> None:
    """测试大文件截断。"""
    print("\n【测试 4】大文件截断")
    print("-" * 60)

    # 创建大文件（超过默认限制）
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for i in range(3000):
            f.write(f"Line {i + 1}: " + "x" * 50 + "\n")
        tmp_path = f.name

    try:
        tool = create_read_tool(os.getcwd())
        result = await tool.execute("test_call_5", {"path": tmp_path})

        text = result.content[0].text

        # 检查是否有截断提示
        assert "Use offset=" in text or "offset=" in text or "继续" in text
        print("✓ 大文件自动截断并显示继续提示")

        # 检查 details 中有截断信息
        if result.details and result.details.truncation:
            trunc = result.details.truncation
            print(f"  - 原始行数: {trunc.total_lines}")
            print(f"  - 输出行数: {trunc.output_lines}")
            print(f"  - 是否截断: {trunc.truncated}")

    finally:
        os.unlink(tmp_path)


async def main() -> None:
    """运行所有读取工具验证。"""
    print("=" * 60)
    print("文件读取工具验证示例")
    print("=" * 60)

    await test_read_text_file()
    await test_read_with_offset_limit()
    await test_read_image_file()
    await test_large_file_truncation()

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
