from __future__ import annotations

from coding_agent.compaction import (
    CompactionSettings,
    create_file_ops,
    estimate_tokens,
)
from coding_agent.session.types import SessionMessageEntry


def test_token_estimation():
    text = "Hello, this is a test message." * 10
    tokens = estimate_tokens(text)
    assert tokens > 0
    ratio = len(text) / tokens
    assert 3.0 <= ratio <= 5.0


def test_should_compact():
    settings = CompactionSettings(enabled=True)
    entries = []
    for i in range(5):
        msg = {"role": "user", "content": "Hello " * 1000}
        entry = SessionMessageEntry(
            id=f"msg{i}",
            parent_id=None if i == 0 else f"msg{i - 1}",
            timestamp="2024-01-01T00:00:00Z",
            message=msg,
        )
        entries.append(entry)

    from coding_agent.compaction import should_compact

    should = should_compact(entries, settings, threshold_tokens=100)
    assert isinstance(should, bool)


def test_file_operations():
    file_ops = create_file_ops()
    assert len(file_ops.read) == 0
    assert len(file_ops.written) == 0
    assert len(file_ops.edited) == 0

    file_ops.read.add("/path/to/file1.txt")
    file_ops.read.add("/path/to/file2.txt")
    file_ops.edited.add("/path/to/file2.txt")
    file_ops.written.add("/path/to/file3.txt")

    assert len(file_ops.read) == 2
    assert len(file_ops.edited) == 1
    assert len(file_ops.written) == 1

    from coding_agent.compaction import compute_file_lists

    read_files, modified_files = compute_file_lists(file_ops)
    assert len(read_files) == 1
    assert len(modified_files) == 2
