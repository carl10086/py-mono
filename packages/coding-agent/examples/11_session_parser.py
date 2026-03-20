#!/usr/bin/env python3
"""
Phase 2 验证示例：会话解析器

验证内容：
1. 解析 JSONL 内容
2. 版本迁移
3. 验证条目

运行方式：
    cd packages/coding-agent && uv run python examples/11_session_parser.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加包路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))

from coding_agent.session.parser import (
    is_valid_session_header,
    migrate_session_entries,
    parse_session_entries,
    validate_session_entries,
)
from coding_agent.session.types import (
    CURRENT_SESSION_VERSION,
    SessionHeader,
    SessionMessageEntry,
)


def test_parse_session() -> None:
    """测试解析会话内容"""
    print("=" * 60)
    print("测试解析会话")
    print("=" * 60)

    # 创建测试 JSONL 内容
    content = """
{"type": "session", "version": 3, "id": "test-session-123", "timestamp": "2024-01-01T00:00:00Z", "cwd": "/test/project"}
{"type": "message", "id": "msg001", "parent_id": null, "timestamp": "2024-01-01T00:00:01Z", "message": {"role": "user", "content": [{"type": "text", "text": "Hello"}], "timestamp": 1704067201000}}
{"type": "thinking_level_change", "id": "think001", "parent_id": "msg001", "timestamp": "2024-01-01T00:00:02Z", "thinking_level": "high"}
{"type": "model_change", "id": "model001", "parent_id": "think001", "timestamp": "2024-01-01T00:00:03Z", "provider": "anthropic", "model_id": "claude-3"}
"""

    entries = parse_session_entries(content)
    print(f"\n解析到 {len(entries)} 个条目:")

    for i, entry in enumerate(entries):
        if isinstance(entry, SessionHeader):
            print(f"  {i}. 头部: id={entry.id}, version={entry.version}")
        elif isinstance(entry, SessionMessageEntry):
            print(f"  {i}. 消息: id={entry.id}, type={entry.type}")
        else:
            print(f"  {i}. 条目: type={entry.type}, id={entry.id}")

    print("\n✓ 解析测试通过")


def test_validation() -> None:
    """测试验证功能"""
    print("\n" + "=" * 60)
    print("测试条目验证")
    print("=" * 60)

    # 有效的头部
    valid_header = {
        "type": "session",
        "id": "test-123",
        "timestamp": "2024-01-01T00:00:00Z",
        "cwd": "/test",
    }
    print(f"\n有效头部: {is_valid_session_header(valid_header)}")

    # 无效的头部
    invalid_header = {
        "type": "message",
        "content": "test",
    }
    print(f"无效头部: {is_valid_session_header(invalid_header)}")

    # 创建条目并验证
    content = """
{"type": "session", "version": 3, "id": "test-123", "timestamp": "2024-01-01T00:00:00Z", "cwd": "/test"}
{"type": "message", "id": "msg001", "parent_id": null, "timestamp": "2024-01-01T00:00:01Z", "message": {"role": "user", "content": "Hello", "timestamp": 1000}}
"""
    entries = parse_session_entries(content)
    errors = validate_session_entries(entries)
    print(f"\n验证结果: {len(errors)} 个错误")
    for error in errors:
        print(f"  - {error}")

    print("\n✓ 验证测试通过")


def test_migration() -> None:
    """测试版本迁移"""
    print("\n" + "=" * 60)
    print("测试版本迁移")
    print("=" * 60)

    # 创建 v1 格式的条目（没有 id/parent_id）
    content = """
{"type": "session", "version": 1, "id": "v1-session", "timestamp": "2024-01-01T00:00:00Z", "cwd": "/test"}
{"type": "message", "timestamp": "2024-01-01T00:00:01Z", "message": {"role": "user", "content": "Hello", "timestamp": 1000}}
"""

    entries = parse_session_entries(content)
    print(f"\n迁移前条目数: {len(entries)}")

    header = next((e for e in entries if isinstance(e, SessionHeader)), None)
    if header:
        print(f"  头部版本: {header.version}")

    # 执行迁移
    migrated = migrate_session_entries(entries)
    print(f"\n是否发生迁移: {migrated}")

    if header:
        print(f"  迁移后版本: {header.version}")
        print(f"  期望版本: {CURRENT_SESSION_VERSION}")

    # 再次迁移（应该不发生）
    migrated_again = migrate_session_entries(entries)
    print(f"\n再次迁移: {migrated_again} (应该为 False)")

    print("\n✓ 迁移测试通过")


def main() -> int:
    """主函数"""
    try:
        test_parse_session()
        test_validation()
        test_migration()

        print("\n" + "=" * 60)
        print("所有测试通过!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
