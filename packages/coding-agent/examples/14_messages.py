#!/usr/bin/env python3
"""
Phase 3.1 验证示例：消息处理

验证内容：
1. BashExecutionMessage 创建和转换
2. CustomMessage 创建
3. BranchSummaryMessage 和 CompactionSummaryMessage 创建
4. convert_to_llm 转换函数

运行方式：
    cd packages/coding-agent && uv run python examples/14_messages.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加包路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))

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
    """测试 Bash 执行消息"""
    print("=" * 60)
    print("测试 BashExecutionMessage")
    print("=" * 60)

    # 创建消息
    msg = BashExecutionMessage(
        command="ls -la",
        output="file1.txt\nfile2.txt",
        exit_code=0,
        cancelled=False,
        truncated=False,
        timestamp=1704067200000,
    )

    print(f"\n命令: {msg.command}")
    print(f"输出: {msg.output[:20]}...")
    print(f"退出码: {msg.exit_code}")
    print(f"时间戳: {msg.timestamp}")

    # 测试转换为文本
    text = bash_execution_to_text(msg)
    print(f"\n转换后的文本:\n{text}")

    # 测试带错误的消息
    error_msg = BashExecutionMessage(
        command="exit 1",
        output="",
        exit_code=1,
        timestamp=1704067200000,
    )
    error_text = bash_execution_to_text(error_msg)
    print(f"\n错误命令转换:\n{error_text}")

    # 测试被取消的消息
    cancelled_msg = BashExecutionMessage(
        command="sleep 10",
        output="",
        exit_code=None,
        cancelled=True,
        timestamp=1704067200000,
    )
    cancelled_text = bash_execution_to_text(cancelled_msg)
    print(f"\n取消命令转换:\n{cancelled_text}")

    # 测试截断的消息
    truncated_msg = BashExecutionMessage(
        command="cat largefile.txt",
        output="...",
        exit_code=0,
        truncated=True,
        full_output_path="/tmp/pi-bash-abc123.log",
        timestamp=1704067200000,
    )
    truncated_text = bash_execution_to_text(truncated_msg)
    print(f"\n截断输出转换:\n{truncated_text}")

    print("\n✓ BashExecutionMessage 测试通过")


def test_custom_message() -> None:
    """测试自定义消息"""
    print("\n" + "=" * 60)
    print("测试 CustomMessage")
    print("=" * 60)

    # 创建文本内容消息
    msg1 = CustomMessage(
        custom_type="testType",
        content="This is a test message",
        display=True,
        details={"key": "value"},
        timestamp=1704067200000,
    )

    print(f"\n自定义类型: {msg1.custom_type}")
    print(f"内容: {msg1.content}")
    print(f"显示: {msg1.display}")
    print(f"详情: {msg1.details}")

    # 创建内容块数组消息
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

    print(f"\n多模态消息:")
    print(f"  类型: {msg2.custom_type}")
    print(f"  内容块数: {len(msg2.content)}")

    # 测试工厂函数
    msg3 = create_custom_message(
        custom_type="factoryTest",
        content="Factory created",
        display=False,
        details=None,
        timestamp="2024-01-01T00:00:00Z",
    )
    print(f"\n工厂函数创建的消息:")
    print(f"  类型: {msg3.custom_type}")
    print(f"  显示: {msg3.display}")

    print("\n✓ CustomMessage 测试通过")


def test_summary_messages() -> None:
    """测试摘要消息"""
    print("\n" + "=" * 60)
    print("测试摘要消息")
    print("=" * 60)

    # 分支摘要
    branch_msg = create_branch_summary_message(
        summary="User asked about file structure",
        from_id="msg001",
        timestamp="2024-01-01T00:00:00Z",
    )

    print(f"\n分支摘要:")
    print(f"  摘要: {branch_msg.summary}")
    print(f"  从 ID: {branch_msg.from_id}")
    print(f"  时间戳: {branch_msg.timestamp}")

    # 压缩摘要
    compaction_msg = create_compaction_summary_message(
        summary="Previous conversation about project setup",
        tokens_before=15000,
        timestamp="2024-01-01T00:00:00Z",
    )

    print(f"\n压缩摘要:")
    print(f"  摘要: {compaction_msg.summary}")
    print(f"  Token 之前: {compaction_msg.tokens_before}")
    print(f"  时间戳: {compaction_msg.timestamp}")

    print("\n✓ 摘要消息测试通过")


def test_convert_to_llm() -> None:
    """测试 convert_to_llm 转换"""
    print("\n" + "=" * 60)
    print("测试 convert_to_llm 转换")
    print("=" * 60)

    # 创建测试消息列表
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
        BranchSummaryMessage(
            summary="Branch summary test",
            from_id="msg001",
            timestamp=3000,
        ),
        CompactionSummaryMessage(
            summary="Compaction summary test",
            tokens_before=10000,
            timestamp=4000,
        ),
    ]

    # 转换为 LLM 格式
    llm_messages = convert_to_llm(messages)

    print(f"\n原始消息数: {len(messages)}")
    print(f"转换后消息数: {len(llm_messages)}")

    for i, msg in enumerate(llm_messages):
        print(f"\n  {i}. role={msg['role']}, timestamp={msg['timestamp']}")
        if isinstance(msg["content"], list) and len(msg["content"]) > 0:
            content_preview = str(msg["content"][0])[:50]
            print(f"     content[0]: {content_preview}...")

    # 测试排除上下文的消息
    excluded_msg = BashExecutionMessage(
        command="secret",
        output="secret output",
        exclude_from_context=True,
        timestamp=5000,
    )
    result = convert_to_llm([excluded_msg])
    print(f"\n排除上下文的消息转换结果数: {len(result)} (应为 0)")
    assert len(result) == 0, "排除的消息不应出现在结果中"

    # 验证常量
    print(f"\n压缩摘要前缀长度: {len(COMPACTION_SUMMARY_PREFIX)}")
    print(f"压缩摘要后缀长度: {len(COMPACTION_SUMMARY_SUFFIX)}")

    print("\n✓ convert_to_llm 测试通过")


def main() -> int:
    """主函数"""
    try:
        test_bash_execution_message()
        test_custom_message()
        test_summary_messages()
        test_convert_to_llm()

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
