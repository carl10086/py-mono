"""Write 工具测试."""

from __future__ import annotations

import os
import tempfile

import pytest

from coding_agent.tools.read import create_read_tool
from coding_agent.tools.write import create_write_tool


@pytest.fixture
def temp_dir():
    """临时目录 fixture."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def write_tool(temp_dir: str):
    """Write tool fixture."""
    return create_write_tool(temp_dir)


@pytest.fixture
def read_tool(temp_dir: str):
    """Read tool fixture."""
    return create_read_tool(temp_dir)


class TestWriteNewFile:
    """测试写入新文件."""

    async def test_write_simple_content(self, write_tool, temp_dir: str) -> None:
        """测试写入简单内容."""
        file_path = os.path.join(temp_dir, "test.txt")
        result = await write_tool.execute(
            "call_1", {"path": "test.txt", "content": "Hello, World!"}
        )

        assert os.path.exists(file_path)
        with open(file_path, encoding="utf-8") as f:
            assert f.read() == "Hello, World!"
        assert result.content[0].type == "text"
        assert "成功写入" in result.content[0].text
        assert "13 字节" in result.content[0].text

    async def test_write_empty_file(self, write_tool, temp_dir: str) -> None:
        """测试写入空文件."""
        file_path = os.path.join(temp_dir, "empty.txt")
        result = await write_tool.execute("call_2", {"path": "empty.txt", "content": ""})

        assert os.path.exists(file_path)
        assert os.path.getsize(file_path) == 0
        assert "0 字节" in result.content[0].text

    async def test_write_binary_content(self, write_tool, temp_dir: str) -> None:
        """测试写入二进制内容（实际是文本）."""
        content = "中文测试\n换行\t制表"
        file_path = os.path.join(temp_dir, "binary.txt")
        await write_tool.execute("call_3", {"path": "binary.txt", "content": content})

        assert os.path.exists(file_path)
        with open(file_path, encoding="utf-8") as f:
            assert f.read() == content


class TestOverwriteFile:
    """测试覆盖现有文件."""

    async def test_overwrite_existing(self, write_tool, temp_dir: str) -> None:
        """测试覆盖已有文件内容."""
        file_path = os.path.join(temp_dir, "existing.txt")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("Old content")

        result = await write_tool.execute(
            "call_4", {"path": "existing.txt", "content": "New content"}
        )

        with open(file_path, encoding="utf-8") as f:
            assert f.read() == "New content"
        assert "成功写入" in result.content[0].text


class TestAutoCreateDirectories:
    """测试自动创建父目录."""

    async def test_create_nested_directories(self, write_tool, temp_dir: str) -> None:
        """测试创建多层嵌套目录."""
        nested_path = os.path.join(temp_dir, "a", "b", "c", "deep.txt")
        await write_tool.execute("call_5", {"path": "a/b/c/deep.txt", "content": "Deep content"})

        assert os.path.exists(nested_path)
        with open(nested_path, encoding="utf-8") as f:
            assert f.read() == "Deep content"

    async def test_create_single_level_directory(self, write_tool, temp_dir: str) -> None:
        """测试创建单层子目录."""
        file_path = os.path.join(temp_dir, "subdir", "file.txt")
        await write_tool.execute("call_6", {"path": "subdir/file.txt", "content": "content"})

        assert os.path.exists(file_path)


class TestWriteReadRoundtrip:
    """测试写入后读取的往返验证."""

    async def test_write_then_read(self, write_tool, read_tool, temp_dir: str) -> None:
        """测试写入后能正确读取."""
        content = "Roundtrip test content"
        await write_tool.execute("write_call", {"path": "roundtrip.txt", "content": content})

        result = await read_tool.execute("read_call", {"path": "roundtrip.txt"})
        assert content in result.content[0].text


class TestWriteToolAttributes:
    """测试工具属性."""

    async def test_tool_name(self, write_tool) -> None:
        """测试工具名称."""
        assert write_tool.name == "write"

    async def test_tool_label(self, write_tool) -> None:
        """测试工具标签."""
        assert write_tool.label == "write"

    async def test_tool_has_description(self, write_tool) -> None:
        """测试工具有描述."""
        assert len(write_tool.description) > 0

    async def test_tool_has_parameters(self, write_tool) -> None:
        """测试工具有参数定义."""
        assert write_tool.parameters is not None
        assert "type" in write_tool.parameters
        assert write_tool.parameters["type"] == "object"
