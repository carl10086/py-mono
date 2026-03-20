from __future__ import annotations

from coding_agent.extensions.types import (
    Extension,
    ExtensionContext,
    ToolDefinition,
)
from coding_agent.extensions.wrapper import (
    clear_registered_tools,
    get_wrapped_tools,
    register_tool,
    wrap_registered_tool,
    wrap_registered_tools,
)


class TestExtension(Extension):
    id = "test-ext"
    name = "Test Extension"
    version = "1.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="hello",
                description="打招呼",
                parameters={"type": "object", "properties": {"name": {"type": "string"}}},
                execute=lambda name: f"Hello, {name}!",
            ),
            ToolDefinition(
                name="add",
                description="加法",
                parameters={
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                },
                execute=lambda a, b: a + b,
            ),
        ]


def test_wrap_registered_tool():
    tool_def = ToolDefinition(
        name="single_tool",
        description="单个工具",
        parameters={},
        execute=lambda: "done",
    )
    wrapped = wrap_registered_tool(tool_def)
    assert wrapped["name"] == "single_tool"
    assert wrapped["description"] == "单个工具"


def test_wrap_registered_tools():
    ext = TestExtension()
    tools = wrap_registered_tools([ext])
    assert "hello" in tools
    assert "add" in tools


def test_register_tool():
    register_tool("custom_tool", {"name": "custom", "execute": lambda: None})
    all_tools = get_wrapped_tools()
    assert "custom_tool" in all_tools


def test_clear_registered_tools():
    clear_registered_tools()
    assert len(get_wrapped_tools()) == 0
