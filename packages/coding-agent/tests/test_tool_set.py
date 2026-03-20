from __future__ import annotations

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
    tools = create_tool_set(".")

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


def test_individual_tools():
    cwd = os.getcwd()

    read_tool = create_read_tool(cwd)
    assert read_tool["name"] == "read"

    write_tool = create_write_tool(cwd)
    assert write_tool["name"] == "write"

    edit_tool = create_edit_tool(cwd)
    assert edit_tool["name"] == "edit"

    bash_tool = create_bash_tool(cwd)
    assert bash_tool["name"] == "bash"

    grep_tool = create_grep_tool(cwd)
    assert grep_tool["name"] == "grep"

    find_tool = create_find_tool(cwd)
    assert find_tool["name"] == "find"

    ls_tool = create_ls_tool(cwd)
    assert ls_tool["name"] == "ls"


def test_tool_execution():
    tools = create_tool_set(".")

    ls_result = tools["ls"]["execute"]("test-1", {"path": "."})
    assert "content" in ls_result

    find_result = tools["find"]["execute"]("test-2", {"pattern": "*.py"})
    assert "content" in find_result

    bash_result = tools["bash"]["execute"]("test-3", {"command": "echo 'test'"})
    assert "content" in bash_result
