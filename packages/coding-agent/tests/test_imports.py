from __future__ import annotations

import coding_agent
from coding_agent.session import SessionEntry, SessionManager
from coding_agent.session.types import SessionMessageEntry


def test_main_imports():
    assert hasattr(coding_agent, "AgentSession")
    assert hasattr(coding_agent, "AgentSessionConfig")
    assert hasattr(coding_agent, "PromptOptions")

    assert hasattr(coding_agent, "BashResult")
    assert hasattr(coding_agent, "execute_bash")

    assert hasattr(coding_agent, "BashExecutionMessage")
    assert hasattr(coding_agent, "CustomMessage")
    assert hasattr(coding_agent, "BranchSummaryMessage")
    assert hasattr(coding_agent, "CompactionSummaryMessage")
    assert hasattr(coding_agent, "ExtendedMessage")
    assert hasattr(coding_agent, "convert_to_llm")

    assert hasattr(coding_agent, "ModelInfo")
    assert hasattr(coding_agent, "ModelRegistry")

    assert hasattr(coding_agent, "SettingsManager")
    assert hasattr(coding_agent, "CompactionSettings")
    assert hasattr(coding_agent, "RetrySettings")

    assert hasattr(coding_agent, "build_system_prompt")

    assert hasattr(coding_agent, "compact")
    assert hasattr(coding_agent, "should_compact")
    assert hasattr(coding_agent, "estimate_tokens")
    assert hasattr(coding_agent, "CompactionConfigSettings")

    assert hasattr(coding_agent, "generate_branch_summary")
    assert hasattr(coding_agent, "BranchSummaryResult")

    assert hasattr(coding_agent, "create_agent_session")
    assert hasattr(coding_agent, "create_coding_tools")
    assert hasattr(coding_agent, "create_read_only_tools")
    assert hasattr(coding_agent, "CreateAgentSessionOptions")
    assert hasattr(coding_agent, "CreateAgentSessionResult")


def test_session_imports():
    from coding_agent.session import SessionManager, SessionEntry
    from coding_agent.session.types import SessionMessageEntry

    assert SessionManager is not None
    assert SessionEntry is not None
    assert SessionMessageEntry is not None


def test_tools_imports():
    from coding_agent.tools import (
        create_read_tool,
        create_write_tool,
        create_edit_tool,
        create_bash_tool,
        create_grep_tool,
        create_find_tool,
        create_ls_tool,
    )

    assert create_read_tool is not None
    assert create_write_tool is not None


def test_compaction_imports():
    from coding_agent.compaction import (
        CompactionSettings,
        compact,
        BranchSummaryResult,
        FileOperations,
    )

    assert compact is not None
    assert CompactionSettings is not None


def test_functional_imports():
    tools = coding_agent.create_coding_tools()
    assert len(tools) >= 4

    result = coding_agent.create_agent_session()
    assert result.session is not None
