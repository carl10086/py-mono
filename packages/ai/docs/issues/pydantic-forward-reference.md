# Pydantic 跨模块前向引用导致代码冗余

## 问题描述

`packages/ai/src/ai/stream.py` 底部需要 12 次重复的 `model_rebuild()` 调用来解决前向引用问题。

### 当前代码（丑陋但工作）

```python
# stream.py 底部
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
```

## 根本原因

**跨模块前向引用（Forward Reference）**

1. Event 类定义在 `stream.py`
2. 但引用了 `types.py` 中的 `AssistantMessage` 和 `ToolCall`
3. Pydantic v2 在类定义时尝试解析类型
4. 类型解析失败（尚未加载）→ 记录为待解析
5. 必须在模块末尾显式调用 `model_rebuild()` 重建

```
stream.py 定义 Event 类 → 引用 AssistantMessage
        ↓                          ↑
        └─── 需要 types.py 导入 ────┘
```

## 尝试失败的方案

### 方案：字符串注解

```python
class EventDone(BaseModel):
    message: "AssistantMessage"  # 字符串形式
```

**失败原因：** Pydantic v2 运行时实例化需要完全解析的类型。字符串注解仅在静态类型检查时有效，运行时仍会报错：

```
PydanticUserError: `EventError` is not fully defined; 
you should define `AssistantMessage`, then call `EventError.model_rebuild()`.
```

## 可行的解决方案

### 方案 A：分层重构（推荐）

将类型按依赖关系分层：

```
ai/
  ├── messages.py   # 基础消息类型
  │   ├── AssistantMessage
  │   ├── UserMessage
  │   └── ToolCall
  ├── events.py     # 事件类型（依赖 messages）
  │   ├── EventStart
  │   ├── EventDone
  │   └── ...
  └── stream.py     # 流逻辑（依赖 events）
      ├── EventStream
      └── AssistantMessageEventStream
```

**依赖方向：** `messages → events → stream`（单向，无前向引用）

**优点：**
- 完全消除 `model_rebuild`
- 代码结构更清晰
- 符合依赖倒置原则

**缺点：**
- 需要重构文件结构
- 更新所有 import 语句

### 方案 B：合并模块

将 `types.py` 和 `stream.py` 中的 Event 类型合并到一个模块：

```python
# ai/protocol.py
class AssistantMessage(BaseModel): ...
class ToolCall(BaseModel): ...

class EventStart(BaseModel):
    partial: AssistantMessage  # 同模块，无问题
```

**优点：**
- 最简单直接
- 零运行时开销

**缺点：**
- 模块变大
- 违反单一职责

## 与 TypeScript 的对比

**pi-mono（TypeScript）无此问题：**

```typescript
// 纯类型定义，编译时检查
export type AssistantMessageEvent =
  | { type: "start"; partial: AssistantMessage }
  | { type: "done"; message: AssistantMessage }

// 运行时是普通对象字面量
stream.push({ type: "start", partial: msg })
```

**Python + Pydantic 必须运行时验证：**

```python
class EventStart(BaseModel):
    partial: AssistantMessage  # 必须运行时解析

# 必须实例化为类
stream.push(EventStart(partial=msg))
```

## 相关文件

- `packages/ai/src/ai/stream.py` - Event 类定义
- `packages/ai/src/ai/types.py` - AssistantMessage 等类型定义

## 优先级

**低** - 当前代码工作正常，只是不够优雅。作为技术债务记录。

## 决策

暂不处理。保持现状，待后续架构重构时统一解决。
