# EventBus 设计文档

> py-mono EventBus 架构与设计说明

---

## 1. 核心问题：EventBus 解决什么问题？

### 1.1 一句话解释

**EventBus = 组件间的"消息广播系统"**

解决的问题：
- 组件间解耦通信（不需要直接引用彼此）
- 扩展间事件传递
- 异步事件处理

### 1.2 为什么需要它？

```
没有 EventBus：
组件 A → 硬编码调用组件 B → 组件 C
（紧密耦合，修改一个影响其他）

有 EventBus：
组件 A → 发布事件 → EventBus → 订阅者收到
组件 B ──────────────────────────┘
组件 C ──────────────────────────┘
（松耦合，通过 EventBus 解耦）
```

---

## 2. 核心概念

### 2.1 发布-订阅模式

```
┌─────────────┐                    ┌──────────────┐
│   发布者    │ ─── emit() ────▶  │  EventBus    │
│  Publisher  │                    │              │
└─────────────┘                    └──────┬───────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
             ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
             │  订阅者 A   │        │  订阅者 B   │        │  订阅者 C   │
             │ Subscriber  │        │ Subscriber  │        │ Subscriber  │
             └─────────────┘        └─────────────┘        └─────────────┘
```

### 2.2 核心 API

| 方法 | 说明 | 示例 |
|------|------|------|
| `emit(channel, data)` | 发布事件 | `bus.emit("user:login", {"user_id": 123})` |
| `on(channel, handler)` | 订阅事件 | `bus.on("user:login", handler)` |
| `clear()` | 清除所有订阅 | `bus.clear()` |

---

## 3. 接口定义

### 3.1 EventBus 接口

```python
class EventBus(Protocol):
    def emit(self, channel: str, data: Any) -> None:
        """发布事件"""
        ...

    def on(self, channel: str, handler: Callable[[Any], Any]) -> Callable[[], None]:
        """订阅事件，返回取消订阅函数"""
        ...
```

### 3.2 EventBusController 接口

```python
class EventBusController(EventBus):
    def clear(self) -> None:
        """清除所有监听器"""
        ...
```

---

## 4. 实际使用场景

### 场景 1：基本发布-订阅

```python
from coding_agent.event_bus import create_event_bus

bus = create_event_bus()

# 订阅
unsub = bus.on("message", lambda data: print(f"收到: {data}"))

# 发布
bus.emit("message", "Hello")
bus.emit("message", "World")

# 取消订阅
unsub()
bus.emit("message", "不会被收到")
```

**为什么需要？**
- 解耦：发布者和订阅者不需要知道彼此的存在
- 灵活：可以随时添加/移除订阅者

### 场景 2：多个订阅者

```python
bus = create_event_bus()

# 多个组件订阅同一事件
def send_email(data):
    print(f"发送邮件: {data}")

def save_to_database(data):
    print(f"保存到数据库: {data}")

def notify_admin(data):
    print(f"通知管理员: {data}")

bus.on("order:created", send_email)
bus.on("order:created", save_to_database)
bus.on("order:created", notify_admin)

# 一个事件触发多个操作
bus.emit("order:created", {"order_id": 123, "total": 99.99})
```

**为什么需要？**
- 一个事件可以触发多个处理逻辑
- 适合"观察者模式"场景

### 场景 3：异步事件处理

```python
import asyncio

bus = create_event_bus()

async def process_data(data):
    # 模拟耗时操作
    await asyncio.sleep(1)
    print(f"处理完成: {data}")

bus.on("data:process", process_data)

# emit 不会阻塞
bus.emit("data:process", "异步数据")
print("emit 立即返回")
```

**为什么需要？**
- 事件处理是异步的，不会阻塞主流程
- 支持 async/await 模式的处理函数

### 场景 4：扩展间通信

```python
# 扩展 A
class ExtensionA:
    def __init__(self, bus):
        self._bus = bus

    def on_load(self):
        self._bus.on("ext_a:request", self._handle)

    def _handle(self, data):
        result = {"from": "A", "data": data}
        self._bus.emit("ext_a:response", result)

# 扩展 B
class ExtensionB:
    def __init__(self, bus):
        self._bus = bus

    def on_load(self):
        self._bus.on("ext_a:response", self._handle_response)

    def send_request(self, data):
        self._bus.emit("ext_a:request", data)

    def _handle_response(self, data):
        print(f"收到响应: {data}")

# 共享同一个 EventBus
shared_bus = create_event_bus()
ext_a = ExtensionA(shared_bus)
ext_b = ExtensionB(shared_bus)

ext_a.on_load()
ext_b.on_load()
ext_b.send_request({"request": "hello"})
```

**为什么需要？**
- 扩展之间不需要直接依赖
- 通过 EventBus 解耦，可以独立开发、测试

### 场景 5：错误隔离

```python
bus = create_event_bus()

def error_handler(_data):
    raise RuntimeError("故意的错误！")

def normal_handler(data):
    print(f"正常处理: {data}")

bus.on("event", error_handler)
bus.on("event", normal_handler)

# error_handler 的异常不会影响 normal_handler
bus.emit("event", "test")
# 输出: 正常处理: test
```

**为什么需要？**
- 一个订阅者的错误不会影响其他订阅者
- 错误被安全捕获并记录

---

## 5. FAQ

### Q: EventBus 和直接函数调用有什么区别？

| 特性 | 直接调用 | EventBus |
|------|----------|----------|
| 耦合度 | 高 | 低 |
| 灵活性 | 低 | 高 |
| 多订阅者 | 需要手动循环 | 自动广播 |
| 动态订阅 | 困难 | 简单 |
| 异步支持 | 需要额外处理 | 原生支持 |

### Q: 什么时候用 EventBus？

- 组件间需要通信但不想直接引用
- 一个事件需要触发多个操作
- 需要动态添加/移除订阅者
- 扩展系统间的通信

### Q: 什么时候不用 EventBus？

- 简单的点对点通信
- 性能敏感的热路径（EventBus 有一定开销）
- 同步依赖关系明确

### Q: EventBus 和 asyncio.Queue 有什么区别？

| 特性 | EventBus | asyncio.Queue |
|------|----------|---------------|
| 模式 | 发布-订阅 | 生产者-消费者 |
| 多订阅者 | ✅ | ❌（每个消息只被一个消费者处理） |
| 同步/异步 | 都支持 | 异步 |
| 消息保留 | ❌（不保留） | ✅（队列保留） |

---

## 6. 与 pi-mono 对比

| 特性 | pi-mono (TypeScript) | py-mono (Python) |
|------|----------------------|------------------|
| emit | ✅ | ✅ |
| on | ✅ | ✅ |
| clear | ✅ | ✅ |
| async 支持 | ✅ | ✅ |
| 错误处理 | ✅ | ✅ |
| Protocol 类型 | ✅ | ✅ |

---

## 7. API 参考

### 7.1 函数

| 函数 | 说明 |
|------|------|
| `create_event_bus()` | 创建 EventBusController 实例 |

### 7.2 EventBusController 方法

| 方法 | 说明 |
|------|------|
| `emit(channel, data)` | 发布事件到指定频道 |
| `on(channel, handler)` | 订阅事件，返回取消订阅函数 |
| `clear()` | 清除所有订阅 |

---

## 8. 测试验证

```bash
cd packages/coding-agent
uv run pytest tests/test_event_bus.py -v
```

**当前测试覆盖**：

| 测试类 | 测试数 | 覆盖内容 |
|--------|--------|----------|
| TestEventBusBasic | 8 | 创建、发布订阅、取消、清空 |
| TestEventBusAsync | 3 | 同步/异步处理器 |
| TestEventBusErrorHandling | 2 | 错误捕获与隔离 |
| TestEventBusEdgeCases | 6 | 边界情况 |

---

## 9. 运行示例

```bash
cd packages/coding-agent
uv run python examples/event_bus_basic.py
```
