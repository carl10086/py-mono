from __future__ import annotations

from coding_agent.slash_commands import (
    SlashCommandRegistry,
    create_default_registry,
    parse_slash_command,
)


def test_parse_slash_command():
    assert parse_slash_command("/help") == ("/help", "")
    assert parse_slash_command("/model gpt-4") == ("/model", "gpt-4")
    assert parse_slash_command("/compact") == ("/compact", "")
    assert parse_slash_command("not a command") is None


def test_create_default_registry():
    registry = create_default_registry()
    commands = registry.list_commands()
    assert len(commands) > 0


def test_registry_get_help_text():
    registry = create_default_registry()
    help_text = registry.get_help_text()
    assert len(help_text) > 0


def test_registry_execute_help():
    registry = create_default_registry()
    result = registry.execute("/help")
    assert result is not None


def test_registry_execute_exit():
    registry = create_default_registry()
    result = registry.execute("/exit")
    assert result is not None


def test_registry_execute_model():
    registry = create_default_registry()
    result = registry.execute("/model gpt-4")
    assert result is not None


def test_custom_command():
    custom_registry = SlashCommandRegistry()

    def custom_handler(arg1: str, arg2: str = "default") -> str:
        return f"自定义命令执行: arg1={arg1}, arg2={arg2}"

    custom_registry.register(
        name="custom",
        description="自定义命令示例",
        handler=custom_handler,
        args_help="[arg1] [arg2]",
    )

    result = custom_registry.execute("/custom value1 value2")
    assert "value1" in result
    assert "value2" in result


def test_unknown_command():
    registry = create_default_registry()
    try:
        registry.execute("/unknown")
        assert False
    except ValueError:
        pass
