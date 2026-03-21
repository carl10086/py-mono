"""EventBus 单元测试"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from coding_agent.event_bus import (
    EventBus,
    EventBusController,
    create_event_bus,
)


class TestEventBusBasic:
    """基本功能测试"""

    def test_create_event_bus(self) -> None:
        """测试创建事件总线"""
        bus = create_event_bus()
        assert hasattr(bus, "emit")
        assert hasattr(bus, "on")
        assert hasattr(bus, "clear")

    def test_emit_without_subscribers(self) -> None:
        """测试无订阅者时 emit 不报错"""
        bus = create_event_bus()
        bus.emit("channel", {"data": "test"})
        bus.emit("nonexistent", None)

    def test_subscribe_and_emit(self) -> None:
        """测试订阅和发布"""
        bus = create_event_bus()
        received: list[Any] = []

        unsub = bus.on("test_channel", lambda d: received.append(d))

        assert len(received) == 0
        bus.emit("test_channel", {"msg": "hello"})
        assert len(received) == 1
        assert received[0] == {"msg": "hello"}

        unsub()

    def test_unsubscribe(self) -> None:
        """测试取消订阅"""
        bus = create_event_bus()
        count = 0

        def increment(data: Any) -> None:
            nonlocal count
            count += 1

        unsub = bus.on("channel", increment)
        bus.emit("channel", None)
        assert count == 1

        unsub()
        bus.emit("channel", None)
        assert count == 1

    def test_multiple_subscribers(self) -> None:
        """测试多个订阅者"""
        bus = create_event_bus()
        results: list[int] = []

        bus.on("channel", lambda _: results.append(1))
        bus.on("channel", lambda _: results.append(2))
        bus.on("channel", lambda _: results.append(3))

        bus.emit("channel", None)
        assert results == [1, 2, 3]

    def test_multiple_channels(self) -> None:
        """测试多个频道"""
        bus = create_event_bus()
        channel_a: list[Any] = []
        channel_b: list[Any] = []

        bus.on("a", lambda d: channel_a.append(d))
        bus.on("b", lambda d: channel_b.append(d))

        bus.emit("a", "from a")
        bus.emit("b", "from b")

        assert channel_a == ["from a"]
        assert channel_b == ["from b"]

    def test_clear(self) -> None:
        """测试清除所有监听"""
        bus = create_event_bus()
        results_a: list[Any] = []
        results_b: list[Any] = []

        bus.on("a", lambda d: results_a.append(d))
        bus.on("b", lambda d: results_b.append(d))

        bus.emit("a", "a1")
        bus.emit("b", "b1")
        assert results_a == ["a1"]
        assert results_b == ["b1"]

        bus.clear()

        bus.emit("a", "a2")
        bus.emit("b", "b2")
        assert results_a == ["a1"]
        assert results_b == ["b1"]

    def test_emit_after_clear_returns(self) -> None:
        """测试 clear 后 emit 不报错"""
        bus = create_event_bus()
        bus.clear()
        bus.emit("channel", "data")


class TestEventBusAsync:
    """异步处理器测试"""

    def test_sync_handler(self) -> None:
        """测试同步处理器"""
        bus = create_event_bus()
        result: list[Any] = []

        def handler(data: Any) -> None:
            result.append(data)

        bus.on("channel", handler)
        bus.emit("channel", "sync_data")
        assert result == ["sync_data"]

    @pytest.mark.asyncio()
    async def test_async_handler(self) -> None:
        """测试异步处理器"""
        bus = create_event_bus()
        result: list[Any] = []

        async def handler(data: Any) -> None:
            await asyncio.sleep(0.01)
            result.append(data)

        bus.on("channel", handler)
        bus.emit("channel", "async_data")
        await asyncio.sleep(0.05)
        assert result == ["async_data"]

    def test_async_handler_no_event_loop(self) -> None:
        """测试无事件循环时异步处理器"""
        bus = create_event_bus()
        result: list[Any] = []

        async def handler(data: Any) -> None:
            await asyncio.sleep(0.01)
            result.append(data)

        bus.on("channel", handler)
        bus.emit("channel", "async_data_no_loop")
        result.append("emitted")
        assert "emitted" in result
        assert "async_data_no_loop" in result


class TestEventBusErrorHandling:
    """错误处理测试"""

    def test_handler_error_caught(self) -> None:
        """测试处理器异常被捕获"""
        bus = create_event_bus()
        results: list[Any] = []

        def error_handler(_data: Any) -> None:
            raise ValueError("Test error")

        def good_handler(data: Any) -> None:
            results.append(data)

        bus.on("channel", error_handler)
        bus.on("channel", good_handler)

        bus.emit("channel", "test")
        assert results == ["test"]

    def test_handler_error_does_not_affect_emit(self) -> None:
        """测试处理器异常不影响 emit"""
        bus = create_event_bus()
        call_count = 0

        def error_handler(_data: Any) -> None:
            raise ValueError("Error")

        bus.on("channel", error_handler)
        bus.on("channel", lambda _: None)

        bus.emit("channel", None)
        bus.emit("channel", None)
        bus.emit("channel", None)


class TestEventBusEdgeCases:
    """边界情况测试"""

    def test_unsubscribe_from_nonexistent_channel(self) -> None:
        """取消订阅不存在的频道"""
        bus = create_event_bus()
        unsub = bus.on("exists", lambda _: None)
        unsub()
        unsub()

    def test_unsubscribe_multiple_times(self) -> None:
        """同一订阅多次取消"""
        bus = create_event_bus()
        unsub = bus.on("channel", lambda _: None)
        unsub()
        unsub()

    def test_emit_with_complex_data(self) -> None:
        """测试发送复杂数据"""
        bus = create_event_bus()
        received: list[Any] = []

        bus.on("channel", lambda d: received.append(d))

        complex_data = {
            "string": "hello",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"a": {"b": "c"}},
            "none": None,
        }
        bus.emit("channel", complex_data)
        assert received == [complex_data]

    def test_on_returns_callable(self) -> None:
        """测试 on 返回可调用对象"""
        bus = create_event_bus()
        unsub = bus.on("channel", lambda _: None)
        assert callable(unsub)

    def test_clear_then_subscribe(self) -> None:
        """测试清除后再订阅"""
        bus = create_event_bus()
        results: list[Any] = []

        bus.on("channel", lambda d: results.append(d))
        bus.clear()
        bus.on("channel", lambda d: results.append(d))

        bus.emit("channel", "after_clear")
        assert results == ["after_clear"]

    def test_closed_bus_ignores_on(self) -> None:
        """测试清除后的总线可以重新订阅"""
        bus = create_event_bus()
        bus.clear()

        unsub = bus.on("channel", lambda _: None)
        unsub()

        results: list[Any] = []
        bus.on("channel", lambda d: results.append(d))
        bus.emit("channel", "after_reclear")
        assert results == ["after_reclear"]
