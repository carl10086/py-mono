"""Bash 工具测试."""

from __future__ import annotations

import os
import tempfile

import pytest

from coding_agent.tools.bash import create_bash_tool


@pytest.fixture
def bash_tool():
    """Bash tool fixture."""
    return create_bash_tool(os.getcwd())


class TestBasicExecution:
    """测试基本命令执行."""

    async def test_echo_command(self, bash_tool) -> None:
        """测试 echo 命令."""
        result = await bash_tool.execute(
            "call_1",
            {"command": "echo 'Hello'"},
        )

        assert "Hello" in result.content[0].text

    async def test_pwd_command(self, bash_tool) -> None:
        """测试 pwd 命令."""
        result = await bash_tool.execute(
            "call_2",
            {"command": "pwd"},
        )

        assert os.getcwd() in result.content[0].text or "/private" in result.content[0].text


class TestErrorHandling:
    """测试错误处理."""

    async def test_exit_code_error(self, bash_tool) -> None:
        """测试非零退出码错误."""
        result = await bash_tool.execute(
            "call_3",
            {"command": "exit 1"},
        )

        assert "exit code 1" in result.content[0].text or "命令退出码: 1" in result.content[0].text

    async def test_invalid_command_error(self, bash_tool) -> None:
        """测试无效命令错误."""
        result = await bash_tool.execute(
            "call_4",
            {"command": "nonexistent_command_xyz"},
        )

        assert "not found" in result.content[0].text.lower() or "找不到" in result.content[0].text


class TestTimeout:
    """测试超时功能."""

    async def test_timeout(self, bash_tool) -> None:
        """测试超时."""
        result = await bash_tool.execute(
            "call_5",
            {"command": "sleep 10", "timeout": 1},
        )

        assert "超时" in result.content[0].text


class TestWorkingDirectory:
    """测试工作目录."""

    async def test_working_directory(self) -> None:
        """测试工作目录切换."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = create_bash_tool(tmpdir)

            result = await tool.execute(
                "call_6",
                {"command": "pwd"},
            )

            assert tmpdir in result.content[0].text


class TestOutputTruncation:
    """测试输出截断."""

    async def test_large_output_truncated(self, bash_tool) -> None:
        """测试大量输出被截断."""
        result = await bash_tool.execute(
            "call_7",
            {"command": "seq 1 3000"},
        )

        assert result.details is not None
        assert result.details.truncation is not None
        assert result.details.truncation.truncated is True


class TestEnvironment:
    """测试环境变量."""

    async def test_environment_variables(self, bash_tool) -> None:
        """测试环境变量继承."""
        result = await bash_tool.execute(
            "call_8",
            {"command": "echo $HOME"},
        )

        assert os.environ.get("HOME", "") in result.content[0].text


class TestToolAttributes:
    """测试工具属性."""

    async def test_tool_name(self, bash_tool) -> None:
        """测试工具名称."""
        assert bash_tool.name == "bash"

    async def test_tool_label(self, bash_tool) -> None:
        """测试工具标签."""
        assert bash_tool.label == "bash"

    async def test_tool_parameters(self, bash_tool) -> None:
        """测试工具参数定义."""
        assert bash_tool.parameters is not None
        assert bash_tool.parameters["type"] == "object"
        assert "command" in bash_tool.parameters["properties"]
