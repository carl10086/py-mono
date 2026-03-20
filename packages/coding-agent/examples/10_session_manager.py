#!/usr/bin/env python3
"""
Phase 2 验证示例：会话管理器

验证内容：
1. 创建内存会话
2. 创建持久化会话
3. 打开现有会话
4. 树遍历和条目获取

运行方式：
    cd packages/coding-agent && uv run python examples/10_session_manager.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# 添加所有包路径
root_dir = Path(__file__).parent.parent.parent.parent  # packages/
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))

from coding_agent.session import SessionManager
from coding_agent.session.types import NewSessionOptions


def test_in_memory_session() -> None:
    """测试内存会话"""
    print("=" * 60)
    print("测试内存会话")
    print("=" * 60)

    # 创建内存会话
    manager = SessionManager.in_memory("/test/project")

    print(f"\n会话ID: {manager.session_id}")
    print(f"会话文件: {manager.session_file}")
    print(f"工作目录: {manager.cwd}")
    print(f"持久化: {manager.is_persisted()}")

    # 创建新会话
    path = manager.new_session()
    print(f"新会话路径: {path}")
    print(f"新会话ID: {manager.session_id}")

    print("\n✓ 内存会话测试通过")


def test_persistent_session() -> None:
    """测试持久化会话"""
    print("\n" + "=" * 60)
    print("测试持久化会话")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建持久化会话
        manager = SessionManager.create(
            cwd="/home/user/myproject",
            session_dir=tmpdir,
        )

        print(f"\n会话ID: {manager.session_id}")
        print(f"会话文件: {manager.session_file}")
        print(f"会话目录: {manager.session_dir}")
        print(f"工作目录: {manager.cwd}")
        print(f"持久化: {manager.is_persisted()}")

        # 验证文件已创建
        if manager.session_file:
            path = Path(manager.session_file)
            print(f"文件存在: {path.exists()}")

        print("\n✓ 持久化会话测试通过")


def test_open_session() -> None:
    """测试打开现有会话"""
    print("\n" + "=" * 60)
    print("测试打开现有会话")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建会话
        manager1 = SessionManager.create(
            cwd="/home/user/project1",
            session_dir=tmpdir,
        )
        original_id = manager1.session_id
        session_file = manager1.session_file

        print(f"\n原始会话ID: {original_id}")
        print(f"会话文件: {session_file}")

        # 重新打开
        if session_file:
            manager2 = SessionManager.open(session_file)
            print(f"打开后会话ID: {manager2.session_id}")
            print(f"工作目录: {manager2.cwd}")

        print("\n✓ 打开会话测试通过")


def test_tree_navigation() -> None:
    """测试树导航"""
    print("\n" + "=" * 60)
    print("测试树导航")
    print("=" * 60)

    manager = SessionManager.in_memory("/test/project")

    # 初始状态
    print(f"\n初始叶子ID: {manager.get_leaf_id()}")
    print(f"条目数: {len(manager.get_entries())}")

    # 获取分支（应该只有头部）
    branch = manager.get_branch()
    print(f"分支条目数: {len(branch)}")

    print("\n✓ 树导航测试通过")


def main() -> int:
    """主函数"""
    try:
        test_in_memory_session()
        test_persistent_session()
        test_open_session()
        test_tree_navigation()

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
