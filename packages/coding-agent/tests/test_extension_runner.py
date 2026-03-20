from __future__ import annotations

from coding_agent.extensions.runner import ExtensionRunner
from coding_agent.extensions.types import (
    Extension,
    ExtensionContext,
    ToolDefinition,
)


class ExtensionA(Extension):
    id = "ext-a"
    name = "Extension A"
    version = "1.0.0"
    activated = False

    def activate(self, ctx: ExtensionContext) -> None:
        self.activated = True

    def deactivate(self) -> None:
        self.activated = False


class ExtensionB(Extension):
    id = "ext-b"
    name = "Extension B"
    version = "2.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="tool_b",
                description="Tool B",
                parameters={},
                execute=lambda: "b",
            )
        ]


def test_extension_runner_activate():
    context = ExtensionContext(
        cwd="/workspace",
        agent_dir="/workspace/.coding-agent",
    )
    runner = ExtensionRunner(context)
    ext_a = ExtensionA()
    ext_b = ExtensionB()
    runner.activate_extension(ext_a)
    runner.activate_extension(ext_b)
    assert len(runner.get_all_extensions()) == 2


def test_extension_runner_get():
    context = ExtensionContext(
        cwd="/workspace",
        agent_dir="/workspace/.coding-agent",
    )
    runner = ExtensionRunner(context)
    ext_a = ExtensionA()
    runner.activate_extension(ext_a)
    ext = runner.get_extension("ext-a")
    assert ext is not None
    assert ext.name == "Extension A"


def test_extension_runner_register_command():
    context = ExtensionContext(
        cwd="/workspace",
        agent_dir="/workspace/.coding-agent",
    )
    runner = ExtensionRunner(context)
    runner.register_command("help", lambda: "帮助信息")
    runner.register_command("exit", lambda: "退出")
    commands = runner.list_commands()
    assert "help" in commands
    assert "exit" in commands


def test_extension_runner_get_tools():
    context = ExtensionContext(
        cwd="/workspace",
        agent_dir="/workspace/.coding-agent",
    )
    runner = ExtensionRunner(context)
    ext_b = ExtensionB()
    runner.activate_extension(ext_b)
    tools = runner.get_all_tools()
    assert len(tools) > 0


def test_extension_runner_deactivate():
    context = ExtensionContext(
        cwd="/workspace",
        agent_dir="/workspace/.coding-agent",
    )
    runner = ExtensionRunner(context)
    ext_a = ExtensionA()
    runner.activate_extension(ext_a)
    runner.deactivate_extension("ext-a")
    assert len(runner.get_all_extensions()) == 0


def test_extension_runner_deactivate_all():
    context = ExtensionContext(
        cwd="/workspace",
        agent_dir="/workspace/.coding-agent",
    )
    runner = ExtensionRunner(context)
    ext_a = ExtensionA()
    ext_b = ExtensionB()
    runner.activate_extension(ext_a)
    runner.activate_extension(ext_b)
    runner.deactivate_all()
    assert len(runner.get_all_extensions()) == 0
