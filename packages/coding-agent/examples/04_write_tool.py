"""文件写入工具验证示例。

验证 write 模块的基本功能：
1. create_write_tool() - 创建写入工具
2. 写入新文件
3. 覆盖现有文件
4. 自动创建父目录
5. 大文件写入测试
"""

from __future__ import annotations

import asyncio
import os
import tempfile

from coding_agent.tools.read import create_read_tool
from coding_agent.tools.write import create_write_tool


async def test_write_new_file() -> None:
    """测试写入新文件。"""
    print("\n【测试 1】写入新文件")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        tool = create_write_tool(tmpdir)
        file_path = os.path.join(tmpdir, "test.txt")

        result = await tool.execute("test_call_1", {"path": "test.txt", "content": "Hello, World!"})

        assert os.path.exists(file_path)
        with open(file_path) as f:
            content = f.read()
        assert content == "Hello, World!"

        assert result.content[0].type == "text"
        assert "成功写入" in result.content[0].text
        assert "13 字节" in result.content[0].text
        print("✓ 成功写入新文件")


async def test_overwrite_existing_file() -> None:
    """测试覆盖现有文件。"""
    print("\n【测试 2】覆盖现有文件")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "existing.txt")

        # 先写入旧内容
        with open(file_path, "w") as f:
            f.write("Old content")

        tool = create_write_tool(tmpdir)
        result = await tool.execute(
            "test_call_2", {"path": "existing.txt", "content": "New content"}
        )

        with open(file_path) as f:
            content = f.read()
        assert content == "New content"
        print("✓ 成功覆盖现有文件")


async def test_auto_create_directories() -> None:
    """测试自动创建父目录。"""
    print("\n【测试 3】自动创建父目录")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        nested_path = os.path.join(tmpdir, "a", "b", "c", "deep.txt")

        tool = create_write_tool(tmpdir)
        result = await tool.execute(
            "test_call_3", {"path": "a/b/c/deep.txt", "content": "Deep content"}
        )

        assert os.path.exists(nested_path)
        with open(nested_path) as f:
            content = f.read()
        assert content == "Deep content"
        print("✓ 成功自动创建多级父目录")


async def test_write_and_read() -> None:
    """测试写入后读取。"""
    print("\n【测试 4】写入后读取验证")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = create_write_tool(tmpdir)
        read_tool = create_read_tool(tmpdir)

        # 写入文件
        await write_tool.execute(
            "write_call", {"path": "roundtrip.txt", "content": "Roundtrip test content"}
        )

        # 读取文件
        result = await read_tool.execute("read_call", {"path": "roundtrip.txt"})

        assert "Roundtrip test content" in result.content[0].text
        print("✓ 写入后读取验证成功")


async def test_write_empty_file() -> None:
    """测试写入空文件。"""
    print("\n【测试 5】写入空文件")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        tool = create_write_tool(tmpdir)

        result = await tool.execute("test_call_5", {"path": "empty.txt", "content": ""})

        file_path = os.path.join(tmpdir, "empty.txt")
        assert os.path.exists(file_path)
        assert os.path.getsize(file_path) == 0
        assert "0 字节" in result.content[0].text
        print("✓ 成功写入空文件")


async def main() -> None:
    """运行所有写入工具验证。"""
    print("=" * 60)
    print("文件写入工具验证示例")
    print("=" * 60)

    await test_write_new_file()
    await test_overwrite_existing_file()
    await test_auto_create_directories()
    await test_write_and_read()
    await test_write_empty_file()

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
