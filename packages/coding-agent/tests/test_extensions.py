from __future__ import annotations

import tempfile
from pathlib import Path

from coding_agent.extensions import (
    Extension,
    ExtensionContext,
    ExtensionRunner,
    ToolDefinition,
    discover_extensions,
    load_extensions,
    wrap_registered_tools,
)


def test_full_extension_system():
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_dir = Path(tmpdir)
        (ext_dir / "my_extension.py").write_text(
            """
from coding_agent.extensions.types import Extension, ExtensionContext, ToolDefinition

class MyExtension(Extension):
    id = "my-ext"
    name = "My Extension"
    version = "1.0.0"
    
    def __init__(self):
        self.tool_calls = 0
    
    def activate(self, context: ExtensionContext) -> None:
        pass
    
    def deactivate(self) -> None:
        pass
    
    def get_tools(self) -> list[ToolDefinition]:
        def count_calls():
            self.tool_calls += 1
            return f"调用次数: {self.tool_calls}"
        
        return [
            ToolDefinition(
                name="count",
                description="计数器",
                parameters={},
                execute=count_calls,
            ),
            ToolDefinition(
                name="echo",
                description="回声",
                parameters={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"}
                    }
                },
                execute=lambda msg: f"Echo: {msg}",
            ),
        ]
"""
        )

        ext_classes = discover_extensions([ext_dir])
        assert len(ext_classes) >= 1

        extensions = load_extensions(ext_classes)
        assert len(extensions) >= 1

        context = ExtensionContext(
            cwd="/workspace",
            agent_dir="/workspace/.coding-agent",
        )
        runner = ExtensionRunner(context)
        activated = runner.activate_all(extensions)
        assert activated >= 1

        tools = wrap_registered_tools(runner.get_all_extensions())
        if "echo" in tools:
            result = tools["echo"]["execute"]("Hello World")
            assert "Echo" in result

        if "count" in tools:
            result = tools["count"]["execute"]()
            assert "调用次数" in result

        runner.deactivate_all()
