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


def _get_tool_name(tool) -> str | None:
    if isinstance(tool, dict):
        return tool.get("name")
    return getattr(tool, "name", None)


def _get_tool_execute(tool):
    if isinstance(tool, dict):
        return tool.get("execute")
    return getattr(tool, "execute", None)


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
        tool_name = _get_tool_name(tool)
        assert tool_name == name, f"{name} 缺少 name"
        assert _get_tool_execute(tool) is not None, f"{name} 缺少 execute"


def test_individual_tools():
    cwd = os.getcwd()

    read_tool = create_read_tool(cwd)
    assert _get_tool_name(read_tool) == "read"

    write_tool = create_write_tool(cwd)
    assert _get_tool_name(write_tool) == "write"

    edit_tool = create_edit_tool(cwd)
    assert _get_tool_name(edit_tool) == "edit"

    bash_tool = create_bash_tool(cwd)
    assert _get_tool_name(bash_tool) == "bash"

    grep_tool = create_grep_tool(cwd)
    assert _get_tool_name(grep_tool) == "grep"

    find_tool = create_find_tool(cwd)
    assert _get_tool_name(find_tool) == "find"

    ls_tool = create_ls_tool(cwd)
    assert _get_tool_name(ls_tool) == "ls"
