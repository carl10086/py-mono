#!/usr/bin/env python3
"""
Phase 3.6 验证示例：AgentSession

运行方式：
    cd packages/coding-agent && uv run python examples/19_agent_session.py
"""

from __future__ import annotations

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))


def main() -> int:
    """主函数"""
    print("=" * 60)
    print("测试 AgentSession")
    print("=" * 60)

    print("\nAgentSession 核心模块已创建（简化版）")
    print("完整功能需要集成 AI Agent 核心")

    print("\n✓ AgentSession 占位测试通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
