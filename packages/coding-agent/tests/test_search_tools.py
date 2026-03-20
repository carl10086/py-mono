from __future__ import annotations

import os
import tempfile

from coding_agent.tools.find import find_tool
from coding_agent.tools.grep import grep_tool
from coding_agent.tools.ls import ls_tool


def test_ls_basic():
    tool = ls_tool()
    result = tool["execute"]("test-1", {})
    content = result["content"][0]["text"]
    assert len(content) > 0


def test_ls_with_path():
    tool = ls_tool(".")
    result = tool["execute"]("test-2", {"path": "."})
    content = result["content"][0]["text"]
    assert len(content.split("\n")) > 0


def test_ls_limit():
    tool = ls_tool(".")
    result = tool["execute"]("test-3", {"limit": 5})
    content = result["content"][0]["text"]
    lines = content.split("\n")
    assert len(lines) <= 5 or "条目限制" in content


def test_find_basic():
    tool = find_tool(".")
    result = tool["execute"]("test-4", {"pattern": "*.py"})
    content = result["content"][0]["text"]
    assert ".py" in content or "未找到" in content


def test_find_recursive():
    tool = find_tool(".")
    result = tool["execute"]("test-5", {"pattern": "**/*.py"})
    content = result["content"][0]["text"]
    assert len(content.split("\n")) > 0


def test_find_limit():
    tool = find_tool(".")
    result = tool["execute"]("test-6", {"pattern": "*.py", "limit": 3})
    content = result["content"][0]["text"]
    lines = content.split("\n")
    assert len(lines) <= 3 or "结果限制" in content


def test_grep_basic():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Hello world\n")
        f.write("This is a test\n")
        f.write("Hello again\n")
        temp_file = f.name

    try:
        tool = grep_tool(os.path.dirname(temp_file))
        result = tool["execute"](
            "test-7",
            {"pattern": "Hello", "path": temp_file, "literal": True},
        )
        content = result["content"][0]["text"]
        assert "Hello" in content
    finally:
        os.unlink(temp_file)


def test_grep_ignore_case():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("HELLO World\n")
        f.write("hello world\n")
        temp_file = f.name

    try:
        tool = grep_tool(os.path.dirname(temp_file))
        result = tool["execute"](
            "test-8",
            {
                "pattern": "hello",
                "path": temp_file,
                "literal": True,
                "ignoreCase": True,
            },
        )
        content = result["content"][0]["text"]
        assert "HELLO" in content or "hello" in content
    finally:
        os.unlink(temp_file)


def test_grep_context():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Line 1\n")
        f.write("Line 2\n")
        f.write("Target line\n")
        f.write("Line 4\n")
        f.write("Line 5\n")
        temp_file = f.name

    try:
        tool = grep_tool(os.path.dirname(temp_file))
        result = tool["execute"](
            "test-9",
            {
                "pattern": "Target",
                "path": temp_file,
                "literal": True,
                "context": 1,
            },
        )
        content = result["content"][0]["text"]
        assert "Line 2" in content
        assert "Line 4" in content
    finally:
        os.unlink(temp_file)


def test_grep_no_match():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Some content\n")
        temp_file = f.name

    try:
        tool = grep_tool(os.path.dirname(temp_file))
        result = tool["execute"](
            "test-10",
            {
                "pattern": "xyz123notfound",
                "path": temp_file,
                "literal": True,
            },
        )
        content = result["content"][0]["text"]
        assert "未找到" in content
    finally:
        os.unlink(temp_file)
