from __future__ import annotations

from coding_agent.compaction import (
    BranchPreparation,
    BranchSummaryDetails,
    BranchSummaryResult,
    CollectEntriesResult,
    collect_entries_for_branch_summary,
    create_file_ops,
    generate_branch_summary,
    prepare_branch_summary,
)
from coding_agent.session.types import SessionMessageEntry


def create_test_entries():
    entries = []
    root = SessionMessageEntry(
        id="root",
        parent_id=None,
        timestamp="2024-01-01T00:00:00Z",
        message={"role": "user", "content": "Root message"},
    )
    entries.append(root)

    a = SessionMessageEntry(
        id="a",
        parent_id="root",
        timestamp="2024-01-01T00:01:00Z",
        message={"role": "assistant", "content": "Branch A response"},
    )
    entries.append(a)

    a1 = SessionMessageEntry(
        id="a1",
        parent_id="a",
        timestamp="2024-01-01T00:02:00Z",
        message={"role": "user", "content": "A1 message"},
    )
    entries.append(a1)

    b = SessionMessageEntry(
        id="b",
        parent_id="root",
        timestamp="2024-01-01T00:01:00Z",
        message={"role": "assistant", "content": "Branch B response"},
    )
    entries.append(b)

    b1 = SessionMessageEntry(
        id="b1",
        parent_id="b",
        timestamp="2024-01-01T00:02:00Z",
        message={"role": "user", "content": "B1 message"},
    )
    entries.append(b1)

    return entries


def test_collect_entries():
    entries = create_test_entries()
    entry_map = {e.id: e for e in entries}

    result = collect_entries_for_branch_summary(
        entries=entries,
        entry_map=entry_map,
        old_leaf_id="a1",
        target_id="b",
    )
    assert len(result.entries) > 0
    assert result.common_ancestor_id is not None


def test_collect_entries_no_old_leaf():
    entries = create_test_entries()
    entry_map = {e.id: e for e in entries}

    result = collect_entries_for_branch_summary(
        entries=entries,
        entry_map=entry_map,
        old_leaf_id=None,
        target_id="a1",
    )
    assert len(result.entries) == 0
    assert result.common_ancestor_id is None


def test_prepare_branch_summary():
    entries = create_test_entries()
    preparation = prepare_branch_summary(entries)
    assert len(preparation.messages) > 0
    assert preparation.total_tokens >= 0


def test_generate_branch_summary():
    entries = create_test_entries()
    result = generate_branch_summary(
        entries=entries,
        from_id="a1",
    )
    assert result.aborted is not None


def test_branch_summary_result_types():
    result = BranchSummaryResult(
        summary="Test summary",
        read_files=["/file1.txt"],
        modified_files=["/file2.txt"],
        aborted=False,
        error=None,
    )
    assert result.summary == "Test summary"
    assert result.read_files == ["/file1.txt"]
    assert result.modified_files == ["/file2.txt"]

    details = BranchSummaryDetails(
        read_files=["/a.txt", "/b.txt"],
        modified_files=["/c.txt"],
    )
    assert details.read_files == ["/a.txt", "/b.txt"]
    assert details.modified_files == ["/c.txt"]

    file_ops = create_file_ops()
    file_ops.read.add("/test.txt")
    prep = BranchPreparation(
        messages=[{"role": "user", "content": "test"}],
        file_ops=file_ops,
        total_tokens=100,
    )
    assert len(prep.messages) == 1
    assert prep.total_tokens == 100

    collect = CollectEntriesResult(
        entries=[],
        common_ancestor_id="root",
    )
    assert len(collect.entries) == 0
    assert collect.common_ancestor_id == "root"
