from __future__ import annotations

from coding_agent.extensions.types import (
    Extension,
    ExtensionContext,
    ToolDefinition,
)


class TestExtension(Extension):
    id = "test-ext"
    name = "Test Extension"
    version = "1.0.0"

    def activate(self, ctx: ExtensionContext) -> None:
        pass

    def deactivate(self) -> None:
        pass

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="my_tool",
                description="My tool",
                parameters={},
                execute=lambda: "result",
            )
        ]


def test_tool_definition():
    tool_def = ToolDefinition(
        name="test_tool",
        description="Test tool",
        parameters={"type": "object", "properties": {}},
        execute=lambda x: x,
    )
    assert tool_def.name == "test_tool"
    assert tool_def.description == "Test tool"


def test_extension_context():
    context = ExtensionContext(
        cwd="/workspace",
        agent_dir="/workspace/.coding-agent",
    )
    assert context.cwd == "/workspace"
    assert context.agent_dir == "/workspace/.coding-agent"


def test_extension():
    ext = TestExtension()
    assert ext.id == "test-ext"
    assert ext.name == "Test Extension"
    assert ext.version == "1.0.0"
    assert len(ext.get_tools()) == 1


def test_extension_lifecycle():
    context = ExtensionContext(
        cwd="/workspace",
        agent_dir="/workspace/.coding-agent",
    )
    ext = TestExtension()
    ext.activate(context)
    ext.deactivate()
