"""
示例工具 - 流式输出处理器

简单的流式输出工具，支持 Claude Code 风格的实时显示。
"""

from __future__ import annotations

from typing import Any

from agent.types import AgentEvent


class StreamingPrinter:
    """流式输出打印机

    模仿 Claude Code 的交互格式：
    - Thinking 阶段: 🤔 思考中...
    - Response 阶段: 📝 回答：
    """

    def __init__(self, show_thinking: bool = True):
        self.show_thinking = show_thinking
        self.thinking_started = False
        self.response_started = False

    def __call__(self, event: AgentEvent) -> None:
        """处理事件"""
        event_type = event.get("type", "")

        if event_type == "message_update":
            self._handle_update(event)

        elif event_type == "message_end":
            self._handle_end()

    def _handle_update(self, event: AgentEvent) -> None:
        """处理流式更新"""
        assistant_event = event.get("assistant_message_event")
        if not assistant_event:
            return

        inner_type = getattr(assistant_event, "type", "")
        delta = getattr(assistant_event, "delta", "")

        if not delta:
            return

        if inner_type == "thinking_delta":
            self._print_thinking(delta)
        elif inner_type == "text_delta":
            self._print_response(delta)

    def _print_thinking(self, text: str) -> None:
        """打印 thinking 内容"""
        if not self.show_thinking:
            return

        if not self.thinking_started:
            print("\n🤔 思考中...")
            self.thinking_started = True

        print(text, end="", flush=True)

    def _print_response(self, text: str) -> None:
        """打印 response 内容"""
        if not self.response_started:
            # 结束 thinking（如果有）
            if self.thinking_started:
                print()
            print("\n📝 回答：")
            self.response_started = True

        print(text, end="", flush=True)

    def _handle_end(self) -> None:
        """处理消息结束"""
        if self.thinking_started or self.response_started:
            print()
            # 重置状态
            self.thinking_started = False
            self.response_started = False


def streaming_printer(show_thinking: bool = True) -> StreamingPrinter:
    """创建流式输出处理器

    参数：
        show_thinking: 是否显示 thinking 内容（如果模型支持）

    使用示例：
        >>> from examples.utils import streaming_printer
        >>> agent.subscribe(streaming_printer())
    """
    return StreamingPrinter(show_thinking=show_thinking)
