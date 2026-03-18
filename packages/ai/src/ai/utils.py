"""
AI 包工具函数和辅助类

提供 StreamWatcher 用于观察和处理流式事件
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ai.stream import (
    AssistantMessageEventStream,
    EventDone,
    EventError,
    EventStart,
    EventTextDelta,
    EventTextEnd,
    EventTextStart,
    EventThinkingDelta,
    EventThinkingEnd,
    EventThinkingStart,
    EventToolCallDelta,
    EventToolCallEnd,
    EventToolCallStart,
)

if TYPE_CHECKING:
    from ai.types import AssistantMessage, ToolCall


type EventHandler[T] = Callable[[T], None] | None


class StreamWatcher:
    """流式事件观察者 - 自动打印事件并提供自定义回调

    使用默认实现时，自动打印所有事件：
        watcher = StreamWatcher()
        message = await watcher.watch(stream)

    自定义特定事件的输出：
        watcher = StreamWatcher(
            on_text=lambda text: print(text, end=""),
            on_thinking=lambda text: print(f"🧠 {text}", end=""),
        )

    完全自定义事件处理：
        watcher = StreamWatcher(
            on_text_start=lambda idx: print(f"[文本开始 {idx}]"),
            on_text_delta=lambda delta: print(delta, end=""),
            on_text_end=lambda: print("[文本结束]"),
        )
    """

    def __init__(
        self,
        # 文本事件回调
        on_text_start: EventHandler[int] = None,
        on_text_delta: EventHandler[str] = None,
        on_text_end: EventHandler[None] = None,
        # 思考事件回调
        on_thinking_start: EventHandler[int] = None,
        on_thinking_delta: EventHandler[str] = None,
        on_thinking_end: EventHandler[None] = None,
        # 工具调用事件回调
        on_toolcall_start: EventHandler[int] = None,
        on_toolcall_delta: EventHandler[str] = None,
        on_toolcall_end: EventHandler[ToolCall] = None,
        # 流生命周期回调
        on_start: EventHandler[None] = None,
        on_done: EventHandler[str] = None,
        on_error: EventHandler[str] = None,
    ) -> None:
        """初始化 StreamWatcher

        所有回调都是可选的，未提供的回调使用默认打印行为
        """
        # 保存自定义回调，None 表示使用默认行为
        self._on_text_start = on_text_start
        self._on_text_delta = on_text_delta
        self._on_text_end = on_text_end
        self._on_thinking_start = on_thinking_start
        self._on_thinking_delta = on_thinking_delta
        self._on_thinking_end = on_thinking_end
        self._on_toolcall_start = on_toolcall_start
        self._on_toolcall_delta = on_toolcall_delta
        self._on_toolcall_end = on_toolcall_end
        self._on_start = on_start
        self._on_done = on_done
        self._on_error = on_error

    async def watch(self, stream: AssistantMessageEventStream) -> AssistantMessage:
        """观察流并处理所有事件

        Args:
            stream: 要观察的事件流

        Returns:
            最终的 AssistantMessage
        """
        async for event in stream:
            match event.type:
                case "start":
                    self._handle_start(event)
                case "text_start":
                    self._handle_text_start(event)
                case "text_delta":
                    self._handle_text_delta(event)
                case "text_end":
                    self._handle_text_end(event)
                case "thinking_start":
                    self._handle_thinking_start(event)
                case "thinking_delta":
                    self._handle_thinking_delta(event)
                case "thinking_end":
                    self._handle_thinking_end(event)
                case "toolcall_start":
                    self._handle_toolcall_start(event)
                case "toolcall_delta":
                    self._handle_toolcall_delta(event)
                case "toolcall_end":
                    self._handle_toolcall_end(event)
                case "done":
                    self._handle_done(event)
                case "error":
                    self._handle_error(event)

        return await stream.result()

    def _handle_start(self, event: EventStart) -> None:
        """处理开始事件"""
        if self._on_start:
            self._on_start()
        # 默认不打印开始事件

    def _handle_text_start(self, event: EventTextStart) -> None:
        """处理文本开始事件"""
        if self._on_text_start:
            self._on_text_start(event.content_index)
        # 默认不打印

    def _handle_text_delta(self, event: EventTextDelta) -> None:
        """处理文本增量事件"""
        if self._on_text_delta:
            self._on_text_delta(event.delta)
        else:
            # 默认打印文本内容
            print(event.delta, end="", flush=True)

    def _handle_text_end(self, event: EventTextEnd) -> None:
        """处理文本结束事件"""
        if self._on_text_end:
            self._on_text_end()
        # 默认不打印

    def _handle_thinking_start(self, event: EventThinkingStart) -> None:
        """处理思考开始事件"""
        if self._on_thinking_start:
            self._on_thinking_start(event.content_index)
        else:
            # 默认打印开始标记
            print("\n🧠 思考开始...", flush=True)

    def _handle_thinking_delta(self, event: EventThinkingDelta) -> None:
        """处理思考增量事件"""
        if self._on_thinking_delta:
            self._on_thinking_delta(event.delta)
        else:
            # 默认打印思考内容
            print(event.delta, end="", flush=True)

    def _handle_thinking_end(self, event: EventThinkingEnd) -> None:
        """处理思考结束事件"""
        if self._on_thinking_end:
            self._on_thinking_end()
        else:
            # 默认打印结束标记
            print("\n✅ 思考结束\n", flush=True)

    def _handle_toolcall_start(self, event: EventToolCallStart) -> None:
        """处理工具调用开始事件"""
        if self._on_toolcall_start:
            self._on_toolcall_start(event.content_index)
        else:
            # 默认打印开始标记
            print(f"\n🔧 工具调用开始 [块 {event.content_index}]\n", flush=True)

    def _handle_toolcall_delta(self, event: EventToolCallDelta) -> None:
        """处理工具调用增量事件"""
        if self._on_toolcall_delta:
            self._on_toolcall_delta(event.delta)
        # 默认不打印（JSON 增量通常不需要显示）

    def _handle_toolcall_end(self, event: EventToolCallEnd) -> None:
        """处理工具调用结束事件"""
        if self._on_toolcall_end:
            self._on_toolcall_end(event.tool_call)
        else:
            # 默认打印工具信息
            tool = event.tool_call
            print(f"\n🔧 工具调用: {tool.name}", flush=True)
            if tool.arguments:
                print(f"   参数: {tool.arguments}", flush=True)

    def _handle_done(self, event: EventDone) -> None:
        """处理完成事件"""
        if self._on_done:
            self._on_done(event.reason)
        else:
            # 默认打印完成信息
            print(f"\n\n✓ 完成 (原因: {event.reason})", flush=True)

    def _handle_error(self, event: EventError) -> None:
        """处理错误事件"""
        if self._on_error:
            self._on_error(event.error.error_message or "未知错误")
        else:
            # 默认打印错误信息
            print(f"\n\n❌ 错误: {event.error.error_message}", flush=True)
