"""
流式事件协议和 EventStream 实现

完全对齐 pi-mono TypeScript 实现：
- 定义 AssistantMessageEvent 流式事件协议
- 实现 EventStream<T, R> 通用事件流收集器
- 实现 AssistantMessageEventStream 特化版本

设计决策：
- EventStream 支持异步迭代协议（AsyncIterable）
- 通过 isComplete/extractResult 回调提取最终结果
- push() 用于发送事件，end() 用于正常结束
- result() 返回最终结果（coroutine）
- 使用 Pydantic BaseModel 定义事件类型（避免 dataclass 字段顺序限制）
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from ai.types import AssistantMessage, StopReason, ToolCall

# ============================================================================
# 流式事件类型 - 对齐 pi-mono types.ts 中的 AssistantMessageEvent
# ============================================================================


class EventStart(BaseModel):
    """流开始事件 - 包含初始 partial AssistantMessage"""

    type: Literal["start"] = "start"
    partial: AssistantMessage | None = None


class EventTextStart(BaseModel):
    """文本块开始"""

    type: Literal["text_start"] = "text_start"
    content_index: int
    partial: AssistantMessage


class EventTextDelta(BaseModel):
    """文本增量"""

    type: Literal["text_delta"] = "text_delta"
    content_index: int
    delta: str
    partial: AssistantMessage


class EventTextEnd(BaseModel):
    """文本块结束"""

    type: Literal["text_end"] = "text_end"
    content_index: int
    content: str
    partial: AssistantMessage


class EventThinkingStart(BaseModel):
    """思考块开始"""

    type: Literal["thinking_start"] = "thinking_start"
    content_index: int
    partial: AssistantMessage


class EventThinkingDelta(BaseModel):
    """思考增量"""

    type: Literal["thinking_delta"] = "thinking_delta"
    content_index: int
    delta: str
    partial: AssistantMessage


class EventThinkingEnd(BaseModel):
    """思考块结束"""

    type: Literal["thinking_end"] = "thinking_end"
    content_index: int
    content: str
    partial: AssistantMessage


class EventToolCallStart(BaseModel):
    """工具调用开始"""

    type: Literal["toolcall_start"] = "toolcall_start"
    content_index: int
    partial: AssistantMessage


class EventToolCallDelta(BaseModel):
    """工具调用参数增量（JSON 流式解析）"""

    type: Literal["toolcall_delta"] = "toolcall_delta"
    content_index: int
    delta: str
    partial: AssistantMessage


class EventToolCallEnd(BaseModel):
    """工具调用结束"""

    type: Literal["toolcall_end"] = "toolcall_end"
    content_index: int
    tool_call: ToolCall
    partial: AssistantMessage


class EventDone(BaseModel):
    """流正常结束 - 包含最终 AssistantMessage"""

    type: Literal["done"] = "done"
    reason: Literal["stop", "length", "toolUse"]
    message: AssistantMessage


class EventError(BaseModel):
    """流错误结束 - 包含错误信息的 AssistantMessage"""

    type: Literal["error"] = "error"
    reason: Literal["aborted", "error"]
    error: AssistantMessage


# 事件联合类型
type AssistantMessageEvent = (
    EventStart
    | EventTextStart
    | EventTextDelta
    | EventTextEnd
    | EventThinkingStart
    | EventThinkingDelta
    | EventThinkingEnd
    | EventToolCallStart
    | EventToolCallDelta
    | EventToolCallEnd
    | EventDone
    | EventError
)

# ============================================================================
# EventStream 通用实现 - 对齐 pi-mono event-stream.ts
# ============================================================================

T = TypeVar("T")
R = TypeVar("R")


class EventStream(Generic[T, R]):
    """通用事件流类 - 支持异步迭代和结果收集

    用于实时消费异步事件流，并在完成时获取最终结果。

    Contract:
    - push(event): 发送事件到流，如果 isComplete(event) 为 true 则标记完成
    - end(result?): 手动结束流，可选指定结果
    - result(): 返回最终结果 coroutine
    - 支持 async for 迭代所有事件

    示例：
        stream = EventStream(is_complete, extract_result)
        async for event in stream:
            print(event)
        result = await stream.result()
    """

    def __init__(
        self,
        is_complete: Callable[[T], bool],
        extract_result: Callable[[T], R],
    ) -> None:
        """初始化事件流

        Args:
            is_complete: 判断事件是否表示流完成的回调
            extract_result: 从完成事件提取最终结果的回调
        """
        self._is_complete = is_complete
        self._extract_result = extract_result
        self._queue: list[T] = []
        self._waiting: list[Callable[[Any], None]] = []
        self._done = False
        self._result: R | None = None
        self._result_resolvers: list[Callable[[R], None]] = []

    def push(self, event: T) -> None:
        """推送事件到流

        如果事件表示完成（is_complete 返回 true），则标记流为完成状态
        并解析最终结果。事件会被发送给等待的消费者或加入队列。
        """
        if self._done:
            return

        # 检查是否是完成事件
        if self._is_complete(event):
            self._done = True
            self._result = self._extract_result(event)
            # 解析等待的 result() 调用
            for resolve in self._result_resolvers:
                resolve(self._result)
            self._result_resolvers.clear()

        # 发送给等待的消费者或加入队列
        if self._waiting:
            waiter = self._waiting.pop(0)
            waiter({"value": event, "done": False})
        else:
            self._queue.append(event)

    def end(self, result: R | None = None) -> None:
        """手动结束流

        Args:
            result: 可选的最终结果，如果不提供则使用已提取的结果
        """
        if self._done:
            return

        self._done = True
        if result is not None:
            self._result = result

        # 解析等待的 result() 调用
        if self._result is not None:
            for resolve in self._result_resolvers:
                resolve(self._result)
            self._result_resolvers.clear()

        # 通知所有等待的消费者流已结束
        while self._waiting:
            waiter = self._waiting.pop(0)
            waiter({"value": None, "done": True})

    def __aiter__(self) -> EventStream[T, R]:
        """返回异步迭代器（self）"""
        return self

    async def __anext__(self) -> T:
        """获取下一个事件

        如果有队列中的事件，立即返回。
        如果流已结束且队列为空，抛出 StopAsyncIteration。
        否则等待新事件到达。
        """
        while True:
            if self._queue:
                return self._queue.pop(0)
            elif self._done:
                raise StopAsyncIteration
            else:
                # 等待新事件
                future: Any = None

                def callback(result: Any) -> None:
                    nonlocal future
                    future = result

                self._waiting.append(callback)

                # 使用 asyncio 等待回调被调用
                import asyncio

                while future is None:
                    await asyncio.sleep(0.001)

                if future.get("done"):
                    raise StopAsyncIteration
                return future["value"]

    async def result(self) -> R:
        """获取最终结果

        如果流已完成，立即返回结果。
        否则等待流完成并返回结果。
        """
        if self._done and self._result is not None:
            return self._result

        import asyncio

        future = asyncio.get_event_loop().create_future()
        self._result_resolvers.append(future.set_result)
        return await future


# ============================================================================
# AssistantMessageEventStream 特化版本
# ============================================================================


class AssistantMessageEventStream(EventStream[AssistantMessageEvent, "AssistantMessage"]):
    """AssistantMessage 事件流 - pi-mono 的核心抽象

    专门用于 AssistantMessageEvent 的 EventStream 特化版本。
    Provider 的 stream() 函数必须返回此类型。

    Contract:
    - 流应该以 EventStart 开始
    - 随后是成对的 _start/_delta/_end 事件（text/thinking/toolcall）
    - 正常结束：EventDone（reason: "stop" | "length" | "toolUse"）
    - 错误结束：EventError（reason: "aborted" | "error"）
    - result() 返回最终的 AssistantMessage

    示例：
        stream = provider.stream(model, context)
        async for event in stream:
            if event.type == "text_delta":
                print(event.delta, end="")
        message = await stream.result()
    """

    def __init__(self) -> None:
        """初始化 AssistantMessage 事件流"""

        def is_complete(event: AssistantMessageEvent) -> bool:
            return isinstance(event, (EventDone, EventError))

        def extract_result(event: AssistantMessageEvent) -> AssistantMessage:
            if isinstance(event, EventDone):
                return event.message
            elif isinstance(event, EventError):
                return event.error
            raise ValueError(f"Unexpected event type for final result: {type(event)}")

        super().__init__(is_complete, extract_result)


def create_assistant_message_event_stream() -> AssistantMessageEventStream:
    """工厂函数：创建 AssistantMessageEventStream

    供 provider 实现和扩展使用。
    """
    return AssistantMessageEventStream()


# ============================================================================
# 工具函数
# ============================================================================


def create_partial_message(
    api: str,
    provider: str,
    model: str,
    content: list[Any] | None = None,
    stop_reason: StopReason = "stop",
) -> AssistantMessage:
    """创建用于事件 partial 字段的部分消息

    在流式事件中使用，构建正在生成的 AssistantMessage 快照。
    """
    from ai.types import Usage, UsageCost

    return AssistantMessage(
        role="assistant",
        content=content or [],
        api=api,
        provider=provider,
        model=model,
        usage=Usage(
            input=0,
            output=0,
            cache_read=0,
            cache_write=0,
            total_tokens=0,
            cost=UsageCost(input=0, output=0, cache_read=0, cache_write=0, total=0),
        ),
        stop_reason=stop_reason,
    )


# ============================================================================
# 解决 Pydantic 前向引用
# ============================================================================

# 在模块加载完成后重建模型，解决前向引用问题
# 需要先导入相关类型，并构建 namespace
from ai.types import AssistantMessage, ToolCall

_rebuild_ns = {
    "AssistantMessage": AssistantMessage,
    "ToolCall": ToolCall,
}

EventStart.model_rebuild(raise_errors=False, _types_namespace=_rebuild_ns)
EventTextStart.model_rebuild(raise_errors=False, _types_namespace=_rebuild_ns)
EventTextDelta.model_rebuild(raise_errors=False, _types_namespace=_rebuild_ns)
EventTextEnd.model_rebuild(raise_errors=False, _types_namespace=_rebuild_ns)
EventThinkingStart.model_rebuild(raise_errors=False, _types_namespace=_rebuild_ns)
EventThinkingDelta.model_rebuild(raise_errors=False, _types_namespace=_rebuild_ns)
EventThinkingEnd.model_rebuild(raise_errors=False, _types_namespace=_rebuild_ns)
EventToolCallStart.model_rebuild(raise_errors=False, _types_namespace=_rebuild_ns)
EventToolCallDelta.model_rebuild(raise_errors=False, _types_namespace=_rebuild_ns)
EventToolCallEnd.model_rebuild(raise_errors=False, _types_namespace=_rebuild_ns)
EventDone.model_rebuild(raise_errors=False, _types_namespace=_rebuild_ns)
EventError.model_rebuild(raise_errors=False, _types_namespace=_rebuild_ns)
