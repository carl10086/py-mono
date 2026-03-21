"""EventBus 模块 - 事件总线系统

提供发布-订阅模式的事件通信机制，用于：
- 组件间解耦通信
- 扩展间事件传递
- 异步事件处理

核心接口：
- EventBus: emit/on 接口
- EventBusController: 增加 clear() 方法

使用方式：
    bus = create_event_bus()

    # 订阅
    unsub = bus.on("my_event", lambda data: print(data))

    # 发布
    bus.emit("my_event", {"key": "value"})

    # 取消订阅
    unsub()

    # 清除所有监听
    bus.clear()
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ============================================================================
# 类型定义
# ============================================================================


@runtime_checkable
class EventBus(Protocol):
    """事件总线接口

    提供基本的事件发布-订阅功能。

    方法：
        emit(channel, data): 发布事件到指定频道
        on(channel, handler): 订阅事件，返回取消订阅函数
    """

    def emit(self, channel: str, data: Any) -> None:
        """发布事件

        Args:
            channel: 事件频道名称
            data: 事件数据（任意类型）
        """
        ...

    def on(
        self, channel: str, handler: Callable[[Any], Awaitable[Any] | Any]
    ) -> Callable[[], None]:
        """订阅事件

        Args:
            channel: 事件频道名称
            handler: 事件处理函数（支持 async 和 sync）

        Returns:
            取消订阅函数，调用后不再接收事件
        """
        ...


class EventBusController(EventBus):
    """事件总线控制器接口

    扩展 EventBus，额外提供 clear() 方法用于清除所有监听器。
    """

    def clear(self) -> None:
        """清除所有监听器

        移除所有频道的订阅关系，之后 emit 将不会触发任何 handler。
        """
        ...


# ============================================================================
# 实现
# ============================================================================


class _EventBusImpl:
    """EventBus 实现类

    使用字典存储每个频道的处理器列表。
    支持 async 和 sync 两种处理器。
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[tuple[Any, Callable[[Any], Any | Awaitable[Any]]]]] = {}

    def emit(self, channel: str, data: Any) -> None:
        """发布事件到指定频道

        Args:
            channel: 事件频道名称
            data: 事件数据
        """
        handlers = self._handlers.get(channel, []).copy()
        for _, handler in handlers:
            try:
                result = handler(data)
                if asyncio.iscoroutine(result):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(result)
                    except RuntimeError:
                        asyncio.run(result)
            except Exception as e:
                logger.error(f"Event handler error ({channel}): {e}", exc_info=e)

    def on(
        self, channel: str, handler: Callable[[Any], Awaitable[Any] | Any]
    ) -> Callable[[], None]:
        """订阅事件

        Args:
            channel: 事件频道名称
            handler: 事件处理函数（支持 async 和 sync）

        Returns:
            取消订阅函数
        """
        wrapper = _SafeHandler(handler, channel)
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append((wrapper, handler))

        def unsubscribe() -> None:
            if channel in self._handlers:
                self._handlers[channel] = [
                    (w, h) for w, h in self._handlers[channel] if h != handler
                ]
                if not self._handlers[channel]:
                    del self._handlers[channel]

        return unsubscribe

    def clear(self) -> None:
        """清除所有监听器"""
        self._handlers.clear()


class _SafeHandler:
    """安全处理器包装器

    捕获并记录处理器中的异常，防止一个处理器的异常
    影响其他处理器或发布者。
    """

    def __init__(self, handler: Callable[[Any], Any | Awaitable[Any]], channel: str) -> None:
        self._handler = handler
        self._channel = channel

    def __call__(self, data: Any) -> None:
        try:
            result = self._handler(data)
            if asyncio.iscoroutine(result):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(result)
                except RuntimeError:
                    asyncio.run(result)
        except Exception as e:
            logger.error(f"Event handler error ({self._channel}): {e}", exc_info=e)


# ============================================================================
# 工厂函数
# ============================================================================


def create_event_bus() -> EventBusController:
    """创建事件总线控制器

    Returns:
        EventBusController 实例，提供 emit/on/clear 方法
    """
    return _EventBusImpl()  # type: ignore[return-value]


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "EventBus",
    "EventBusController",
    "create_event_bus",
]
