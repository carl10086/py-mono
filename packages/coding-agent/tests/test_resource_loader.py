from __future__ import annotations

import tempfile
from pathlib import Path

from coding_agent.resource_loader import (
    DefaultResourceLoader,
    InMemoryResourceLoader,
    ResourceNotFoundError,
)


def test_in_memory_resource_loader():
    mem_loader = InMemoryResourceLoader()
    mem_loader.add_resource("greeting", "Hello, World!")
    mem_loader.add_resource("config", '{"version": "1.0"}')

    assert "greeting" in mem_loader.list_resources()
    assert mem_loader.exists("greeting")
    assert not mem_loader.exists("unknown")

    text = mem_loader.load_text("greeting")
    assert text == "Hello, World!"

    json_data = mem_loader.load_json("config")
    assert json_data["version"] == "1.0"


def test_resource_not_found():
    mem_loader = InMemoryResourceLoader()
    try:
        mem_loader.load_text("nonexistent")
        assert False
    except ResourceNotFoundError:
        pass


def test_default_resource_loader():
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        (base_path / "messages").mkdir()
        (base_path / "messages" / "welcome.txt").write_text("欢迎！")
        (base_path / "config.json").write_text('{"debug": true}')

        loader = DefaultResourceLoader(base_path)
        resources = loader.list_resources()
        assert len(resources) > 0

        welcome = loader.load_text("messages.welcome")
        assert welcome == "欢迎！"

        config = loader.load_json("config")
        assert config["debug"] is True

        assert loader.exists("messages.welcome")
        assert not loader.exists("missing")
