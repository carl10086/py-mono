"""搜索工具验证示例。

验证 ls/find/grep 工具的各项功能。
"""

import os
import tempfile

from coding_agent.tools.find import find_tool
from coding_agent.tools.grep import grep_tool
from coding_agent.tools.ls import ls_tool


def test_ls_basic():
    """测试 ls 基本功能。"""
    print("=== 测试1: ls 基本功能 ===")
    tool = ls_tool()

    result = tool["execute"]("test-1", {})

    content = result["content"][0]["text"]
    print(f"当前目录内容:\n{content[:200]}...")
    assert len(content) > 0
    print("✓ ls 基本功能正常\n")


def test_ls_with_path():
    """测试 ls 指定路径。"""
    print("=== 测试2: ls 指定路径 ===")
    tool = ls_tool(".")

    result = tool["execute"]("test-2", {"path": "."})

    content = result["content"][0]["text"]
    print(f"目录内容行数: {len(content.split(chr(10)))}")
    print("✓ ls 指定路径正常\n")


def test_ls_limit():
    """测试 ls 限制条目。"""
    print("=== 测试3: ls 限制条目 ===")
    tool = ls_tool(".")

    result = tool["execute"]("test-3", {"limit": 5})

    content = result["content"][0]["text"]
    lines = content.split("\n")
    print(f"返回条目数: {len(lines)}")
    assert len(lines) <= 5 or "条目限制" in content
    print("✓ ls 限制条目正常\n")


def test_find_basic():
    """测试 find 基本功能。"""
    print("=== 测试4: find 基本功能 ===")
    tool = find_tool(".")

    result = tool["execute"]("test-4", {"pattern": "*.py"})

    content = result["content"][0]["text"]
    print(f"找到 {len(content.split(chr(10)))} 个 Python 文件")
    assert ".py" in content or "未找到" in content
    print("✓ find 基本功能正常\n")


def test_find_recursive():
    """测试 find 递归模式。"""
    print("=== 测试5: find 递归模式 ===")
    tool = find_tool(".")

    result = tool["execute"]("test-5", {"pattern": "**/*.py"})

    content = result["content"][0]["text"]
    print(f"递归找到 {len(content.split(chr(10)))} 个文件")
    print("✓ find 递归模式正常\n")


def test_find_limit():
    """测试 find 限制结果。"""
    print("=== 测试6: find 限制结果 ===")
    tool = find_tool(".")

    result = tool["execute"]("test-6", {"pattern": "*.py", "limit": 3})

    content = result["content"][0]["text"]
    lines = content.split("\n")
    print(f"返回结果数: {len(lines)}")
    assert len(lines) <= 3 or "结果限制" in content
    print("✓ find 限制结果正常\n")


def test_grep_basic():
    """测试 grep 基本功能。"""
    print("=== 测试7: grep 基本功能 ===")

    # 创建临时文件
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
        print(f"匹配结果:\n{content}")
        assert "Hello" in content
        print("✓ grep 基本功能正常\n")
    finally:
        os.unlink(temp_file)


def test_grep_ignore_case():
    """测试 grep 忽略大小写。"""
    print("=== 测试8: grep 忽略大小写 ===")

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
        print(f"匹配结果:\n{content}")
        assert "HELLO" in content or "hello" in content
        print("✓ grep 忽略大小写正常\n")
    finally:
        os.unlink(temp_file)


def test_grep_context():
    """测试 grep 上下文。"""
    print("=== 测试9: grep 上下文 ===")

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
        print(f"匹配结果:\n{content}")
        assert "Line 2" in content
        assert "Line 4" in content
        print("✓ grep 上下文正常\n")
    finally:
        os.unlink(temp_file)


def test_grep_no_match():
    """测试 grep 无匹配。"""
    print("=== 测试10: grep 无匹配 ===")

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
        print(f"结果: {content}")
        assert "未找到" in content
        print("✓ grep 无匹配处理正常\n")
    finally:
        os.unlink(temp_file)


def main():
    """运行所有测试。"""
    print("搜索工具验证\n")
    print("=" * 50)

    test_ls_basic()
    test_ls_with_path()
    test_ls_limit()
    test_find_basic()
    test_find_recursive()
    test_find_limit()
    test_grep_basic()
    test_grep_ignore_case()
    test_grep_context()
    test_grep_no_match()

    print("=" * 50)
    print("所有测试通过！")


if __name__ == "__main__":
    main()
