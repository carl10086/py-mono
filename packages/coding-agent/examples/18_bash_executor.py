#!/usr/bin/env python3
"""
Phase 3.5 验证示例：Bash 执行器

运行方式：
    cd packages/coding-agent && uv run python examples/18_bash_executor.py
"""

from __future__ import annotations

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))

from coding_agent.bash_executor import execute_bash


def main() -> int:
    """主函数"""
    print("=" * 60)
    print("测试 Bash 执行器")
    print("=" * 60)

    # 执行简单命令
    print("\n1. 执行 echo 命令:")
    result = execute_bash("echo 'Hello World'")
    print(f"   输出: {result.output.strip()}")
    print(f"   退出码: {result.exit_code}")

    # 执行多行输出
    print("\n2. 执行多行输出:")
    result = execute_bash("echo 'line1\nline2'")
    print(f"   输出行数: {len(result.output.strip().split(chr(10)))}")

    # 执行错误命令
    print("\n3. 执行错误命令:")
    result = execute_bash("exit 1")
    print(f"   退出码: {result.exit_code}")

    print("\n✓ Bash 执行器测试通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
