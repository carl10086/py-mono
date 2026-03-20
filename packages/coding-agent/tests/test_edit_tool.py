"""Edit 工具测试."""

from __future__ import annotations

import os
import tempfile

import pytest

from coding_agent.tools.edit import create_edit_tool


@pytest.fixture
def temp_dir():
    """临时目录 fixture."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def edit_tool(temp_dir: str):
    """Edit tool fixture."""
    return create_edit_tool(temp_dir)


class TestExactReplace:
    """测试精确文本替换."""

    async def test_simple_replace(self, edit_tool, temp_dir: str) -> None:
        """测试简单文本替换."""
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("Hello, World!\nThis is a test.")

        result = await edit_tool.execute(
            "call_1",
            {"path": "test.txt", "oldText": "Hello, World!", "newText": "Hi, Universe!"},
        )

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        assert "Hi, Universe!" in content
        assert "Hello, World!" not in content
        assert "成功" in result.content[0].text


class TestFuzzyMatch:
    """测试模糊匹配."""

    async def test_smart_quotes_match(self, edit_tool, temp_dir: str) -> None:
        """测试智能引号匹配."""
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write('print("Hello World")')

        await edit_tool.execute(
            "call_3",
            {
                "path": "test.txt",
                "oldText": 'print("Hello World")',
                "newText": 'print("Hi Universe")',
            },
        )

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        assert "Hi Universe" in content


class TestErrorHandling:
    """测试错误处理."""

    async def test_file_not_found(self, edit_tool, temp_dir: str) -> None:
        """测试文件不存在错误."""
        result = await edit_tool.execute(
            "call_4",
            {"path": "nonexistent.txt", "oldText": "foo", "newText": "bar"},
        )

        assert "编辑失败" in result.content[0].text
        assert "文件不存在" in result.content[0].text

    async def test_text_not_found(self, edit_tool, temp_dir: str) -> None:
        """测试文本未找到错误."""
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("Hello World")

        result = await edit_tool.execute(
            "call_5",
            {"path": "test.txt", "oldText": "Not Found Text", "newText": "bar"},
        )

        assert "编辑失败" in result.content[0].text
        assert "找到精确的文本" in result.content[0].text

    async def test_multiple_occurrences_error(self, edit_tool, temp_dir: str) -> None:
        """测试多次匹配错误."""
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("repeat\nrepeat\nrepeat")

        result = await edit_tool.execute(
            "call_6",
            {"path": "test.txt", "oldText": "repeat", "newText": "changed"},
        )

        assert "编辑失败" in result.content[0].text
        assert "唯一的" in result.content[0].text


class TestLineEndings:
    """测试换行符处理."""

    async def test_crlf_preserved(self, edit_tool, temp_dir: str) -> None:
        """测试 CRLF 换行符保留."""
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "wb") as f:
            f.write(b"Line 1\r\nLine 2\r\nLine 3")

        await edit_tool.execute(
            "call_7",
            {"path": "test.txt", "oldText": "Line 2", "newText": "Modified Line 2"},
        )

        with open(file_path, "rb") as f:
            content_bytes = f.read()

        assert b"\r\n" in content_bytes


class TestDiffOutput:
    """测试差异输出."""

    async def test_diff_details(self, edit_tool, temp_dir: str) -> None:
        """测试差异详情."""
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("foo\nbar\nbaz")

        result = await edit_tool.execute(
            "call_8",
            {"path": "test.txt", "oldText": "bar", "newText": "qux"},
        )

        assert result.details is not None
        assert result.details.diff is not None
        assert len(result.details.diff) > 0
        assert "qux" in result.details.diff


class TestToolAttributes:
    """测试工具属性."""

    async def test_tool_name(self, edit_tool) -> None:
        """测试工具名称."""
        assert edit_tool.name == "edit"

    async def test_tool_label(self, edit_tool) -> None:
        """测试工具标签."""
        assert edit_tool.label == "edit"

    async def test_tool_has_parameters(self, edit_tool) -> None:
        """测试工具有参数定义."""
        assert edit_tool.parameters is not None
        assert edit_tool.parameters["type"] == "object"
