from __future__ import annotations

import tempfile
from pathlib import Path

from coding_agent.settings_manager import (
    CompactionSettings,
    RetrySettings,
    Settings,
    SettingsManager,
)


def test_in_memory_settings() -> None:
    settings = Settings(
        default_provider="anthropic",
        default_model="claude-3",
        default_thinking_level="medium",
    )
    manager = SettingsManager.in_memory(settings)

    assert manager.get_default_provider() == "anthropic"
    assert manager.get_default_model() == "claude-3"
    assert manager.get_default_thinking_level() == "medium"

    manager.set_default_provider("openai")
    assert manager.get_default_provider() == "openai"


def test_compaction_settings() -> None:
    manager = SettingsManager.in_memory()
    compaction = manager.get_compaction_settings()
    assert isinstance(compaction, CompactionSettings)
    assert compaction.enabled is True

    global_settings = manager.get_global_settings()
    global_settings.compaction.enabled = False
    assert global_settings.compaction.enabled is False


def test_retry_settings() -> None:
    manager = SettingsManager.in_memory()
    retry = manager.get_retry_settings()
    assert isinstance(retry, RetrySettings)
    assert retry.enabled is True

    global_settings = manager.get_global_settings()
    global_settings.retry.enabled = False
    assert global_settings.retry.enabled is False


def test_file_settings() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / ".pi" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text('{"default_provider": "test-provider"}')

        manager = SettingsManager.create(cwd=tmpdir, agent_dir=tmpdir)
        assert manager.get_default_provider() == "test-provider"


def test_settings_merge() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        agent_dir = Path(tmpdir) / "agent"
        agent_dir.mkdir()
        global_file = agent_dir / "settings.json"
        global_file.write_text('{"default_provider": "global-provider", "theme": "dark"}')

        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        pi_dir = project_dir / ".pi"
        pi_dir.mkdir()
        project_file = pi_dir / "settings.json"
        project_file.write_text('{"default_provider": "project-provider"}')

        manager = SettingsManager.create(cwd=str(project_dir), agent_dir=str(agent_dir))
        assert manager.get_default_provider() == "project-provider"
        assert manager.get_theme() == "dark"
