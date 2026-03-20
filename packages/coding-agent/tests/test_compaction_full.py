from __future__ import annotations

from coding_agent.compaction import (
    CompactionSettings,
    TOOL_RESULT_MAX_CHARS,
    SUMMARIZATION_SYSTEM_PROMPT,
    compact,
    compute_file_lists,
    create_file_ops,
    estimate_context_tokens,
    extract_file_ops_from_message,
    format_file_operations,
    prepare_compaction,
    should_compact,
)
from coding_agent.session.types import SessionMessageEntry


def test_full_compaction_workflow():
    entries = []
    for i in range(50):
        role = "user" if i % 2 == 0 else "assistant"
        content = f"Message {i}: " + "This is some content that adds up. " * 20
        msg = {"role": role, "content": content}
        entry = SessionMessageEntry(
            id=f"msg{i:03d}",
            parent_id=None if i == 0 else f"msg{i - 1:03d}",
            timestamp="2024-01-01T00:00:00Z",
            message=msg,
        )
        entries.append(entry)

    settings = CompactionSettings(enabled=True, keep_recent_tokens=2000)
    estimated = estimate_context_tokens(entries)
    assert estimated >= 0

    needs = should_compact(entries, settings, threshold_tokens=5000)
    assert isinstance(needs, bool)

    prep = prepare_compaction(entries, settings)
    assert prep.first_kept_entry_id is not None
    assert prep.tokens_before >= 0

    result = compact(entries, settings)
    if result:
        assert len(result.summary) > 0


def test_file_operations_integration():
    file_ops = create_file_ops()
    files_read = ["/src/main.py", "/src/utils.py", "/README.md"]
    files_written = ["/src/main.py"]
    files_edited = ["/src/utils.py"]

    for f in files_read:
        file_ops.read.add(f)
    for f in files_written:
        file_ops.written.add(f)
    for f in files_edited:
        file_ops.edited.add(f)

    assert len(file_ops.read) == 3
    assert len(file_ops.written) == 1
    assert len(file_ops.edited) == 1

    read_files, modified_files = compute_file_lists(file_ops)
    assert len(read_files) == 2
    assert len(modified_files) == 2

    formatted = format_file_operations(read_files, modified_files)
    assert len(formatted) > 0


def test_branch_summary_integration():
    entries = []
    for i in range(5):
        entry = SessionMessageEntry(
            id=f"main{i}",
            parent_id=None if i == 0 else f"main{i - 1}",
            timestamp=f"2024-01-01T00:0{i}:00Z",
            message={"role": "user" if i % 2 == 0 else "assistant", "content": f"Main {i}"},
        )
        entries.append(entry)

    for i in range(3):
        entry = SessionMessageEntry(
            id=f"branch_a{i}",
            parent_id="main4" if i == 0 else f"branch_a{i - 1}",
            timestamp=f"2024-01-01T00:1{i}:00Z",
            message={"role": "user" if i % 2 == 0 else "assistant", "content": f"Branch A {i}"},
        )
        entries.append(entry)

    for i in range(3):
        entry = SessionMessageEntry(
            id=f"branch_b{i}",
            parent_id="main4" if i == 0 else f"branch_b{i - 1}",
            timestamp=f"2024-01-01T00:2{i}:00Z",
            message={"role": "user" if i % 2 == 0 else "assistant", "content": f"Branch B {i}"},
        )
        entries.append(entry)

    entry_map = {e.id: e for e in entries}

    from coding_agent.compaction import (
        collect_entries_for_branch_summary,
        generate_branch_summary,
        prepare_branch_summary,
    )

    collect_result = collect_entries_for_branch_summary(
        entries=entries,
        entry_map=entry_map,
        old_leaf_id="branch_a2",
        target_id="branch_b2",
    )
    assert len(collect_result.entries) > 0
    assert collect_result.common_ancestor_id is not None

    prep = prepare_branch_summary(entries)
    assert len(prep.messages) > 0
    assert prep.total_tokens >= 0

    summary_result = generate_branch_summary(
        entries=collect_result.entries,
        from_id="branch_a2",
    )
    assert summary_result.aborted is not None


def test_constants():
    assert TOOL_RESULT_MAX_CHARS > 0
    assert len(SUMMARIZATION_SYSTEM_PROMPT) > 0
