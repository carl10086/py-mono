from __future__ import annotations

from ai.types import ImageContent, TextContent
from coding_agent.messages import (
    COMPACTION_SUMMARY_PREFIX,
    COMPACTION_SUMMARY_SUFFIX,
    BashExecutionMessage,
    BranchSummaryMessage,
    CompactionSummaryMessage,
    CustomMessage,
    bash_execution_to_text,
    convert_to_llm,
    create_branch_summary_message,
    create_compaction_summary_message,
    create_custom_message,
)


def test_bash_execution_message() -> None:
    msg = BashExecutionMessage(
        command="ls -la",
        output="file1.txt\nfile2.txt",
        exit_code=0,
        cancelled=False,
        truncated=False,
        timestamp=1704067200000,
    )
    assert msg.command == "ls -la"
    assert msg.exit_code == 0

    text = bash_execution_to_text(msg)
    assert "ls -la" in text

    error_msg = BashExecutionMessage(
        command="exit 1",
        output="",
        exit_code=1,
        timestamp=1704067200000,
    )
    error_text = bash_execution_to_text(error_msg)
    assert "exit 1" in error_text or "exit code 1" in error_text

    cancelled_msg = BashExecutionMessage(
        command="sleep 10",
        output="",
        exit_code=None,
        cancelled=True,
        timestamp=1704067200000,
    )
    cancelled_text = bash_execution_to_text(cancelled_msg)
    assert cancelled_text is not None


def test_custom_message() -> None:
    msg1 = CustomMessage(
        custom_type="testType",
        content="This is a test message",
        display=True,
        details={"key": "value"},
        timestamp=1704067200000,
    )
    assert msg1.custom_type == "testType"
    assert msg1.display is True

    content_blocks = [
        TextContent(text="Text part"),
        ImageContent(data="base64data", mime_type="image/png"),
    ]
    msg2 = CustomMessage(
        custom_type="multiModal",
        content=content_blocks,
        display=True,
        details=None,
        timestamp=1704067200000,
    )
    assert msg2.custom_type == "multiModal"
    assert len(msg2.content) == 2


def test_summary_messages() -> None:
    branch_msg = create_branch_summary_message(
        summary="User asked about file structure",
        from_id="msg001",
        timestamp="2024-01-01T00:00:00Z",
    )
    assert branch_msg.summary == "User asked about file structure"
    assert branch_msg.from_id == "msg001"

    compaction_msg = create_compaction_summary_message(
        summary="Previous conversation about project setup",
        tokens_before=15000,
        timestamp="2024-01-01T00:00:00Z",
    )
    assert compaction_msg.summary == "Previous conversation about project setup"
    assert compaction_msg.tokens_before == 15000


def test_convert_to_llm() -> None:
    messages = [
        BashExecutionMessage(
            command="echo hello",
            output="hello",
            exit_code=0,
            timestamp=1000,
        ),
        CustomMessage(
            custom_type="test",
            content="Custom message",
            display=True,
            timestamp=2000,
        ),
    ]

    llm_messages = convert_to_llm(messages)
    assert len(llm_messages) == 2

    excluded_msg = BashExecutionMessage(
        command="secret",
        output="secret output",
        exclude_from_context=True,
        timestamp=5000,
    )
    result = convert_to_llm([excluded_msg])
    assert len(result) == 0

    assert len(COMPACTION_SUMMARY_PREFIX) > 0
    assert len(COMPACTION_SUMMARY_SUFFIX) > 0
