from __future__ import annotations

from coding_agent.sdk import (
    CreateAgentSessionOptions,
    create_agent_session,
    create_coding_tools,
    create_read_only_tools,
)


def test_create_coding_tools():
    tools = create_coding_tools()
    assert len(tools) > 0
    assert "read" in tools
    assert "bash" in tools
    assert "edit" in tools
    assert "write" in tools

    tools_cwd = create_coding_tools("/tmp/test")
    assert len(tools_cwd) > 0


def test_create_read_only_tools():
    tools = create_read_only_tools()
    assert len(tools) > 0
    assert "read" in tools
    assert "grep" in tools
    assert "find" in tools
    assert "ls" in tools
    assert "bash" in tools

    tools_cwd = create_read_only_tools("/home/user/project")
    assert len(tools_cwd) > 0


def test_create_agent_session_minimal():
    result = create_agent_session()
    assert result.session is not None
    assert hasattr(result.session, "agent")
    assert hasattr(result.session, "session_manager")
    assert hasattr(result.session, "settings_manager")


def test_create_agent_session_custom():
    custom_tools = list(create_read_only_tools().values())
    options = CreateAgentSessionOptions(
        cwd="/tmp/test-project",
        tools=custom_tools,
    )
    result = create_agent_session(options)
    assert result.session._cwd == "/tmp/test-project"


def test_create_agent_session_with_model():
    class FakeModel:
        def __init__(self):
            self.id = "fake-model"
            self.provider = "fake-provider"

    fake_model = FakeModel()
    options = CreateAgentSessionOptions(model=fake_model)
    result = create_agent_session(options)
    assert result.session.agent.model == fake_model


def test_sdk_types():
    opts = CreateAgentSessionOptions(
        cwd="/test",
        agent_dir="/agent",
    )
    assert opts.cwd == "/test"
    assert opts.agent_dir == "/agent"

    result = create_agent_session()
    assert result.session is not None
