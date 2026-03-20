from __future__ import annotations

from coding_agent.bash_executor import execute_bash


def test_execute_bash_echo():
    result = execute_bash("echo 'Hello World'")
    assert result.output.strip() == "Hello World"
    assert result.exit_code == 0


def test_execute_bash_multiline():
    result = execute_bash("echo 'line1\nline2'")
    lines = result.output.strip().split("\n")
    assert len(lines) == 2


def test_execute_bash_exit_code():
    result = execute_bash("exit 1")
    assert result.exit_code == 1
