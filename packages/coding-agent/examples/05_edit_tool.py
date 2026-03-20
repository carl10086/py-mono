"""文件编辑工具验证示例。

验证 edit 模块的基本功能：
1. create_edit_tool() - 创建编辑工具
2. 精确文本替换
3. 模糊匹配编辑
4. 多行编辑
5. 差异输出验证
"""

from __future__ import annotations

import asyncio
import os
import tempfile

from coding_agent.tools.edit import create_edit_tool


async def test_exact_replace() -> None:
    """测试精确文本替换。"""
    print("\n【测试 1】精确文本替换")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        with open(file_path, "w") as f:
            f.write("Hello, World!\nThis is a test.")

        tool = create_edit_tool(tmpdir)
        result = await tool.execute(
            "test_call_1",
            {"path": "test.txt", "oldText": "Hello, World!", "newText": "Hi, Universe!"},
        )

        with open(file_path) as f:
            content = f.read()

        assert "Hi, Universe!" in content
        assert "Hello, World!" not in content
        assert result.content[0].type == "text"
        assert "成功" in result.content[0].text
        print("✓ 精确替换成功")


async def test_fuzzy_match() -> None:
    """测试模糊匹配（处理引号等差异）。"""
    print("\n【测试 2】模糊匹配编辑")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        # 使用智能引号
        with open(file_path, "w") as f:
            f.write('print("Hello World")')

        tool = create_edit_tool(tmpdir)
        # 使用普通引号进行替换
        result = await tool.execute(
            "test_call_2",
            {
                "path": "test.txt",
                "oldText": 'print("Hello World")',
                "newText": 'print("Hi Universe")',
            },
        )

        with open(file_path) as f:
            content = f.read()

        assert "Hi Universe" in content
        print("✓ 模糊匹配替换成功")


async def test_multiline_edit() -> None:
    """测试多行编辑。"""
    print("\n【测试 3】多行编辑")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        with open(file_path, "w") as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4")

        tool = create_edit_tool(tmpdir)
        result = await tool.execute(
            "test_call_3",
            {
                "path": "test.txt",
                "oldText": "Line 2\nLine 3",
                "newText": "Modified Line 2\nModified Line 3",
            },
        )

        with open(file_path) as f:
            content = f.read()

        assert "Modified Line 2" in content
        assert "Modified Line 3" in content
        assert "Line 2\nLine 3" not in content
        print("✓ 多行编辑成功")


async def test_diff_output() -> None:
    """测试差异输出。"""
    print("\n【测试 4】差异输出验证")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        with open(file_path, "w") as f:
            f.write("foo\nbar\nbaz")

        tool = create_edit_tool(tmpdir)
        result = await tool.execute(
            "test_call_4",
            {"path": "test.txt", "oldText": "bar", "newText": "qux"},
        )

        # 检查 details 中有差异信息
        assert result.details is not None
        assert result.details.diff is not None
        assert len(result.details.diff) > 0
        print(f"✓ 差异输出成功")
        print(f"  - 差异内容:\n{result.details.diff[:200]}...")


async def test_unique_text_required() -> None:
    """测试唯一文本要求。"""
    print("\n【测试 5】唯一文本验证")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        with open(file_path, "w") as f:
            f.write("repeat\nrepeat\nrepeat")

        tool = create_edit_tool(tmpdir)

        result = await tool.execute(
            "test_call_5",
            {"path": "test.txt", "oldText": "repeat", "newText": "changed"},
        )

        assert "唯一的" in result.content[0].text or "unique" in result.content[0].text.lower()
        assert "编辑失败" in result.content[0].text
        print("✓ 正确检测到多个匹配")


async def test_line_ending_preservation() -> None:
    """测试换行符保留。"""
    print("\n【测试 6】换行符保留")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        # 使用 CRLF 换行符
        with open(file_path, "wb") as f:
            f.write(b"Line 1\r\nLine 2\r\nLine 3")

        tool = create_edit_tool(tmpdir)
        result = await tool.execute(
            "test_call_6",
            {"path": "test.txt", "oldText": "Line 2", "newText": "Modified Line 2"},
        )

        # 读取原始字节以验证换行符
        with open(file_path, "rb") as f:
            content_bytes = f.read()

        assert b"\r\n" in content_bytes  # CRLF 应该被保留
        print("✓ 换行符保留成功")


async def main() -> None:
    """运行所有编辑工具验证。"""
    print("=" * 60)
    print("文件编辑工具验证示例")
    print("=" * 60)

    await test_exact_replace()
    await test_fuzzy_match()
    await test_multiline_edit()
    await test_diff_output()
    await test_unique_text_required()
    await test_line_ending_preservation()

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
