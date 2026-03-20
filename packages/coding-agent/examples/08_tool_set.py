"""工具集合验证示例。

验证 create_tool_set 和工具包导入。
"""

import os

from coding_agent.tools import (
    create_bash_tool,
    create_edit_tool,
    create_find_tool,
    create_grep_tool,
    create_ls_tool,
    create_read_tool,
    create_tool_set,
    create_write_tool,
)


def test_create_tool_set():
    """测试工具集合创建。"""
    print("=== 测试: create_tool_set ===")

    tools = create_tool_set(".")

    print(f"工具数量: {len(tools)}")
    print(f"可用工具: {', '.join(tools.keys())}")

    assert "read" in tools
    assert "write" in tools
    assert "edit" in tools
    assert "bash" in tools
    assert "grep" in tools
    assert "find" in tools
    assert "ls" in tools

    for name, tool in tools.items():
        assert "name" in tool, f"{name} 缺少 name"
        assert "label" in tool, f"{name} 缺少 label"
        assert "description" in tool, f"{name} 缺少 description"
        assert "parameters" in tool, f"{name} 缺少 parameters"
        assert "execute" in tool, f"{name} 缺少 execute"

    print("✓ 工具集合创建成功\n")


def test_individual_tools():
    """测试单独创建工具。"""
    print("=== 测试: 单独创建工具 ===")

    cwd = os.getcwd()

    read_tool = create_read_tool(cwd)
    assert read_tool["name"] == "read"
    print("✓ read 工具")

    write_tool = create_write_tool(cwd)
    assert write_tool["name"] == "write"
    print("✓ write 工具")

    edit_tool = create_edit_tool(cwd)
    assert edit_tool["name"] == "edit"
    print("✓ edit 工具")

    bash_tool = create_bash_tool(cwd)
    assert bash_tool["name"] == "bash"
    print("✓ bash 工具")

    grep_tool = create_grep_tool(cwd)
    assert grep_tool["name"] == "grep"
    print("✓ grep 工具")

    find_tool = create_find_tool(cwd)
    assert find_tool["name"] == "find"
    print("✓ find 工具")

    ls_tool = create_ls_tool(cwd)
    assert ls_tool["name"] == "ls"
    print("✓ ls 工具")

    print("✓ 所有工具创建成功\n")


def test_tool_execution():
    """测试工具执行。"""
    print("=== 测试: 工具执行 ===")

    tools = create_tool_set(".")

    # 测试 ls
    ls_result = tools["ls"]["execute"]("test-1", {"path": "."})
    assert "content" in ls_result
    print(f"✓ ls 执行成功，返回 {len(ls_result['content'][0]['text'].split(chr(10)))} 行")

    # 测试 find
    find_result = tools["find"]["execute"]("test-2", {"pattern": "*.py"})
    assert "content" in find_result
    print(f"✓ find 执行成功")

    # 测试 bash
    bash_result = tools["bash"]["execute"]("test-3", {"command": "echo 'test'"})
    assert "content" in bash_result
    print(f"✓ bash 执行成功")

    print("✓ 工具执行测试通过\n")


def main():
    """运行所有测试。"""
    print("工具集合验证\n")
    print("=" * 50)

    test_create_tool_set()
    test_individual_tools()
    test_tool_execution()

    print("=" * 50)
    print("所有测试通过！")
    print("\nPhase 1 基础设施与工具集完成！")


if __name__ == "__main__":
    main()
