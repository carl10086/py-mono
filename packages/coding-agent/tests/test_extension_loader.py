from __future__ import annotations

import tempfile
from pathlib import Path

from coding_agent.extensions.loader import (
    discover_extensions,
    load_extension,
    load_extensions,
)


def test_discover_extensions():
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_dir = Path(tmpdir)
        ext_file = ext_dir / "test_extension.py"
        ext_file.write_text(
            """
from coding_agent.extensions.types import Extension, ExtensionContext, ToolDefinition

class TestExtension(Extension):
    id = "test-ext"
    name = "Test Extension"
    version = "1.0.0"

    def activate(self, context: ExtensionContext) -> None:
        pass

    def deactivate(self) -> None:
        pass

    def get_tools(self) -> list[ToolDefinition]:
        return []
"""
        )

        ext_classes = discover_extensions([ext_dir])
        assert len(ext_classes) >= 1


def test_load_extension():
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_dir = Path(tmpdir)
        ext_file = ext_dir / "test_extension.py"
        ext_file.write_text(
            """
from coding_agent.extensions.types import Extension, ExtensionContext, ToolDefinition

class TestExtension(Extension):
    id = "test-ext"
    name = "Test Extension"
    version = "1.0.0"

    def activate(self, context: ExtensionContext) -> None:
        pass

    def deactivate(self) -> None:
        pass

    def get_tools(self) -> list[ToolDefinition]:
        return []
"""
        )

        ext_classes = discover_extensions([ext_dir])
        if ext_classes:
            ext = load_extension(ext_classes[0])
            assert ext.name == "Test Extension"


def test_load_extensions():
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_dir = Path(tmpdir)
        ext_file = ext_dir / "test_extension.py"
        ext_file.write_text(
            """
from coding_agent.extensions.types import Extension, ExtensionContext, ToolDefinition

class TestExtension(Extension):
    id = "test-ext"
    name = "Test Extension"
    version = "1.0.0"

    def activate(self, context: ExtensionContext) -> None:
        pass

    def deactivate(self) -> None:
        pass

    def get_tools(self) -> list[ToolDefinition]:
        return []
"""
        )

        ext_classes = discover_extensions([ext_dir])
        if ext_classes:
            exts = load_extensions(ext_classes)
            assert len(exts) >= 1
