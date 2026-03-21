"""EventBus 使用示例

展示 EventBus 的基本用法：
1. 创建事件总线
2. 订阅事件
3. 发布事件
4. 取消订阅
5. 清除所有监听

运行：
    cd packages/coding-agent
    uv run python examples/event_bus_basic.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from coding_agent.event_bus import EventBus, EventBusController, create_event_bus


def sync_handler(data: object) -> None:
    """同步事件处理器"""
    print(f"  [sync] 收到事件: {data}")


async def async_handler(data: object) -> None:
    """异步事件处理器"""
    print(f"  [async] 收到事件: {data}")
    await asyncio.sleep(0.1)
    print(f"  [async] 处理完成: {data}")


def main() -> None:
    print("=" * 60)
    print("EventBus 基本示例")
    print("=" * 60)

    bus: EventBusController = create_event_bus()

    print("\n1. 基本发布-订阅")
    print("-" * 40)
    unsub = bus.on("channel_a", sync_handler)
    bus.emit("channel_a", {"message": "Hello"})
    unsub()
    bus.emit("channel_a", {"message": "不会收到这条"})
    print("  [main] unsub() 后不再收到事件")

    print("\n2. 多个订阅者")
    print("-" * 40)
    unsub1 = bus.on("channel_b", lambda d: print(f"  [handler1] {d}"))
    unsub2 = bus.on("channel_b", lambda d: print(f"  [handler2] {d}"))
    unsub3 = bus.on("channel_b", lambda d: print(f"  [handler3] {d}"))
    bus.emit("channel_b", "所有订阅者都收到")
    unsub1()
    unsub2()
    unsub3()
    bus.emit("channel_b", "所有订阅者都已取消")

    print("\n3. 异步处理器")
    print("-" * 40)
    bus.on("channel_c", async_handler)
    bus.emit("channel_c", {"async": True})
    print("  [main] 异步处理器正在后台运行...")
    asyncio.run(asyncio.sleep(0.2))

    print("\n4. 错误处理")
    print("-" * 40)

    def error_handler(_data: object) -> None:
        raise ValueError("故意的错误！")

    bus.on("channel_d", error_handler)
    bus.on("channel_d", sync_handler)
    bus.emit("channel_d", "错误被捕获，不影响其他处理器")
    print("  [main] 错误被安全捕获")

    print("\n5. 清除所有监听")
    print("-" * 40)
    bus.on("channel_e", lambda d: print(f"  [e1] {d}"))
    bus.on("channel_e", lambda d: print(f"  [e2] {d}"))
    bus.on("channel_f", lambda d: print(f"  [f1] {d}"))
    print("  清除前:")
    bus.emit("channel_e", "channel_e 消息")
    bus.emit("channel_f", "channel_f 消息")
    bus.clear()
    print("  清除后:")
    bus.emit("channel_e", "channel_e 消息（不会收到）")
    bus.emit("channel_f", "channel_f 消息（不会收到）")

    print("\n6. 扩展间通信模式")
    print("-" * 40)

    class ExtensionA:
        def __init__(self, bus: EventBus) -> None:
            self._bus = bus

        def on_load(self) -> None:
            self._bus.on("ext_a:request", self._handle_request)
            print("  [ExtA] 已加载，监听 ext_a:request")

        def _handle_request(self, data: object) -> None:
            result = {"from": "ExtensionA", "data": data, "processed": True}
            self._bus.emit("ext_a:response", result)
            print(f"  [ExtA] 处理请求，发送响应")

    class ExtensionB:
        def __init__(self, bus: EventBus) -> None:
            self._bus = bus
            self._pending_requests: list[object] = []

        def on_load(self) -> None:
            self._bus.on("ext_a:response", self._handle_response)
            print("  [ExtB] 已加载，监听 ext_a:response")

        def send_request(self, data: str) -> None:
            self._bus.emit("ext_a:request", {"request_id": 1, "data": data})
            print(f"  [ExtB] 发送请求: {data}")

        def _handle_response(self, data: object) -> None:
            self._pending_requests.append(data)
            print(f"  [ExtB] 收到响应: {data}")

    shared_bus = create_event_bus()
    ext_a = ExtensionA(shared_bus)
    ext_b = ExtensionB(shared_bus)

    ext_a.on_load()
    ext_b.on_load()
    ext_b.send_request("ExtensionB 请求 ExtensionA 处理")

    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
