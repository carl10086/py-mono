from __future__ import annotations

from coding_agent.tools.truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    format_size,
    truncate_head,
    truncate_line,
    truncate_tail,
)


def test_format_size() -> None:
    assert format_size(0) == "0B"
    assert format_size(512) == "512B"
    assert format_size(1023) == "1023B"
    assert format_size(1024) == "1.0KB"
    assert format_size(1536) == "1.5KB"
    assert format_size(1024 * 1024 - 1) == "1024.0KB"
    assert format_size(1024 * 1024) == "1.0MB"
    assert format_size(1024 * 1024 * 5) == "5.0MB"


def test_truncate_head() -> None:
    small_content = "line1\nline2\nline3"
    result = truncate_head(small_content, max_lines=10, max_bytes=1000)
    assert result.truncated is False
    assert result.content == small_content
    assert result.output_lines == 3

    lines_content = "\n".join([f"line{i}" for i in range(100)])
    result = truncate_head(lines_content, max_lines=50, max_bytes=10000)
    assert result.truncated is True
    assert result.truncated_by == "lines"
    assert result.output_lines == 50
    assert "line0" in result.content
    assert "line49" in result.content
    assert "line50" not in result.content

    long_line = "x" * 1000
    content = "\n".join([long_line for _ in range(10)])
    result = truncate_head(content, max_lines=100, max_bytes=500)
    assert result.truncated is True
    assert result.truncated_by == "bytes"

    huge_line = "x" * 10000
    result = truncate_head(huge_line, max_lines=10, max_bytes=100)
    assert result.truncated is True
    assert result.first_line_exceeds_limit is True
    assert result.output_lines == 0


def test_truncate_tail() -> None:
    small_content = "line1\nline2\nline3"
    result = truncate_tail(small_content, max_lines=10, max_bytes=1000)
    assert result.truncated is False
    assert result.content == small_content

    lines_content = "\n".join([f"line{i}" for i in range(100)])
    result = truncate_tail(lines_content, max_lines=50, max_bytes=10000)
    assert result.truncated is True
    assert result.truncated_by == "lines"
    assert result.output_lines == 50
    assert "line99" in result.content
    assert "line50" in result.content
    assert "line49" not in result.content

    long_line = "x" * 1000
    content = "\n".join([long_line for _ in range(10)])
    result = truncate_tail(content, max_lines=100, max_bytes=500)
    assert result.truncated is True
    assert result.truncated_by == "bytes"


def test_truncate_line() -> None:
    short_line = "short text"
    result, was_truncated = truncate_line(short_line, max_chars=100)
    assert result == short_line
    assert was_truncated is False

    long_line = "x" * 1000
    result, was_truncated = truncate_line(long_line, max_chars=100)
    assert was_truncated is True
    assert len(result) < len(long_line)
    assert "[截断]" in result

    exact_line = "x" * 100
    result, was_truncated = truncate_line(exact_line, max_chars=100)
    assert was_truncated is False
    assert result == exact_line


def test_large_file() -> None:
    large_content = "\n".join([f"This is line number {i:04d} with some text" for i in range(5000)])
    content_size = len(large_content)

    head_result = truncate_head(large_content)
    assert head_result.output_lines <= DEFAULT_MAX_LINES
    assert "This is line number 0000" in head_result.content

    tail_result = truncate_tail(large_content)
    assert tail_result.output_lines <= DEFAULT_MAX_LINES
    assert "This is line number 4999" in tail_result.content
