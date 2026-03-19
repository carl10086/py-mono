"""截断工具验证示例。

验证 truncate 模块的基本功能：
1. format_size() - 字节大小格式化
2. truncate_head() - 头部截断
3. truncate_tail() - 尾部截断
4. truncate_line() - 行级截断
"""

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
    """测试大小格式化功能。"""
    print("\n【测试 1】format_size() - 大小格式化")
    print("-" * 60)

    # 字节级别
    assert format_size(0) == "0B"
    assert format_size(512) == "512B"
    assert format_size(1023) == "1023B"
    print("✓ 字节级别 (0-1023)")

    # KB级别
    assert format_size(1024) == "1.0KB"
    assert format_size(1536) == "1.5KB"
    assert format_size(1024 * 1024 - 1) == "1024.0KB"
    print("✓ KB级别 (1KB - 1MB)")

    # MB级别
    assert format_size(1024 * 1024) == "1.0MB"
    assert format_size(1024 * 1024 * 5) == "5.0MB"
    print("✓ MB级别 (>= 1MB)")

    print("\n大小格式化测试通过！")


def test_truncate_head() -> None:
    """测试头部截断功能。"""
    print("\n【测试 2】truncate_head() - 头部截断")
    print("-" * 60)

    # 无需截断的小内容
    small_content = "line1\nline2\nline3"
    result = truncate_head(small_content, max_lines=10, max_bytes=1000)
    assert result.truncated is False
    assert result.content == small_content
    assert result.output_lines == 3
    print("✓ 小内容无需截断")

    # 按行截断
    lines_content = "\n".join([f"line{i}" for i in range(100)])
    result = truncate_head(lines_content, max_lines=50, max_bytes=10000)
    assert result.truncated is True
    assert result.truncated_by == "lines"
    assert result.output_lines == 50
    assert "line0" in result.content
    assert "line49" in result.content
    assert "line50" not in result.content
    print("✓ 按行截断正确（保留前50行）")

    # 按字节截断
    long_line = "x" * 1000
    content = "\n".join([long_line for _ in range(10)])
    result = truncate_head(content, max_lines=100, max_bytes=500)
    assert result.truncated is True
    assert result.truncated_by == "bytes"
    print("✓ 按字节截断正确")

    # 第一行超出限制的特殊情况
    huge_line = "x" * 10000
    result = truncate_head(huge_line, max_lines=10, max_bytes=100)
    assert result.truncated is True
    assert result.first_line_exceeds_limit is True
    assert result.output_lines == 0
    print("✓ 第一行超出字节限制检测正确")

    print("\n头部截断测试通过！")


def test_truncate_tail() -> None:
    """测试尾部截断功能。"""
    print("\n【测试 3】truncate_tail() - 尾部截断")
    print("-" * 60)

    # 无需截断的小内容
    small_content = "line1\nline2\nline3"
    result = truncate_tail(small_content, max_lines=10, max_bytes=1000)
    assert result.truncated is False
    assert result.content == small_content
    print("✓ 小内容无需截断")

    # 按行截断
    lines_content = "\n".join([f"line{i}" for i in range(100)])
    result = truncate_tail(lines_content, max_lines=50, max_bytes=10000)
    assert result.truncated is True
    assert result.truncated_by == "lines"
    assert result.output_lines == 50
    assert "line99" in result.content
    assert "line50" in result.content
    assert "line49" not in result.content
    print("✓ 按行截断正确（保留后50行）")

    # 按字节截断
    long_line = "x" * 1000
    content = "\n".join([long_line for _ in range(10)])
    result = truncate_tail(content, max_lines=100, max_bytes=500)
    assert result.truncated is True
    assert result.truncated_by == "bytes"
    print("✓ 按字节截断正确")

    # 检查默认常量
    print(f"✓ 默认最大行数: {DEFAULT_MAX_LINES}")
    print(f"✓ 默认最大字节数: {format_size(DEFAULT_MAX_BYTES)}")

    print("\n尾部截断测试通过！")


def test_truncate_line() -> None:
    """测试行级截断功能。"""
    print("\n【测试 4】truncate_line() - 行级截断")
    print("-" * 60)

    # 短行无需截断
    short_line = "short text"
    result, was_truncated = truncate_line(short_line, max_chars=100)
    assert result == short_line
    assert was_truncated is False
    print("✓ 短行无需截断")

    # 长行需要截断
    long_line = "x" * 1000
    result, was_truncated = truncate_line(long_line, max_chars=100)
    assert was_truncated is True
    assert len(result) < len(long_line)
    assert "[截断]" in result
    print("✓ 长行正确截断")

    # 边界情况
    exact_line = "x" * 100
    result, was_truncated = truncate_line(exact_line, max_chars=100)
    assert was_truncated is False
    assert result == exact_line
    print("✓ 边界情况处理正确（恰好100字符）")

    print("\n行级截断测试通过！")


def test_large_file() -> None:
    """测试大文件截断场景。"""
    print("\n【测试 5】大文件截断场景")
    print("-" * 60)

    # 生成大文件内容（5000行）
    large_content = "\n".join([f"This is line number {i:04d} with some text" for i in range(5000)])
    content_size = len(large_content)

    print(f"原始内容: {5000} 行, {format_size(content_size)}")

    # 头部截断
    head_result = truncate_head(large_content)
    print(f"头部截断后: {head_result.output_lines} 行, {format_size(head_result.output_bytes)}")
    assert head_result.output_lines <= DEFAULT_MAX_LINES
    assert "This is line number 0000" in head_result.content

    # 尾部截断
    tail_result = truncate_tail(large_content)
    print(f"尾部截断后: {tail_result.output_lines} 行, {format_size(tail_result.output_bytes)}")
    assert tail_result.output_lines <= DEFAULT_MAX_LINES
    assert "This is line number 4999" in tail_result.content

    print("\n大文件截断测试通过！")


def main() -> None:
    """运行所有截断工具验证。"""
    print("=" * 60)
    print("截断工具验证示例")
    print("=" * 60)

    test_format_size()
    test_truncate_head()
    test_truncate_tail()
    test_truncate_line()
    test_large_file()

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    main()
