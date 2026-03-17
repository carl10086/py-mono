# AI 模块实现方案

## 目标

实现 AI 核心层，提供统一的 LLM Provider 抽象。仅支持 Anthropic 模型，Python 3.12+，Pyright Strict 零错误。

---

## 架构原则

### 1. 分层抽象

- **类型层**: 统一消息、工具、模型定义（Pydantic）
- **协议层**: Provider 接口抽象（Protocol）
- **实现层**: Anthropic Provider 具体实现
- **管理层**: 上下文管理和 Token 计算

### 2. 关键设计决策

**为什么用 Protocol 而非 ABC?**
- 结构子类型，第三方实现无需继承
- 更好的类型推断和编辑器支持
- 避免强耦合的继承体系

**为什么用 Pydantic v2?**
- 严格的类型验证和序列化
- 与 Python 类型系统深度集成
- 支持复杂的嵌套模型定义

**为什么用 AsyncIterator 流式?**
- 实时响应，低延迟体验
- 内存友好，支持超长生成
- 原生支持 Anthropic 的 SSE 流

---

## 核心组件

### 1. 类型系统

**消息统一抽象**
- UserMessage: 文本 + 图像内容
- AssistantMessage: 文本 + 工具调用 + 思考过程
- ToolResultMessage: 工具执行结果

**工具定义 Schema**
- ToolDefinition: 名称、描述、参数列表
- 参数类型: string/number/boolean/array/object
- 支持 enum 限制和必填标记

### 2. Provider 注册表

**全局注册机制**
- 模块导入时自注册
- 运行时动态获取
- 支持测试时 mock 替换

**协议接口**
- stream(): 异步流式生成
- get_model(): 模型配置查询
- models: 支持的模型列表

### 3. 流式事件协议

**事件类型设计**
- Start/Complete: 生命周期标记
- TextDelta: 文本增量（支持多内容块）
- ThinkingDelta: 思考过程（Anthropic 特有）
- ToolCallStart/Delta: 工具调用流式解析
- Usage: Token 使用统计
- Error: 错误信息（带错误码）

**收集器模式**
- StreamCollector: 收集事件组装完整消息
- 适用于非实时 UI 场景
- 自动处理增量合并

### 4. Anthropic 适配

**类型转换**
- 内部消息格式 ↔ Anthropic Message API
- ToolDefinition ↔ Anthropic Tool Schema
- 流事件实时转换（无需缓冲）

**模型配置**
- Claude Opus 4: 强推理，高成本
- Claude Sonnet 4: 平衡性能，推荐默认
- 统一 Model 元数据（context_window, cost等）

**认证方式**
- 环境变量 ANTHROPIC_API_KEY
- 参数传入 api_key（覆盖环境变量）
- 支持自定义 base_url

### 5. 上下文管理

**Token 计算**
- Tiktoken cl100k_base 编码
- 消息、工具、system_prompt 分别计算
- 预留格式开销（4 tokens/消息）

**剪枝策略**
- 保留 system_prompt（最高优先级）
- 从最新消息向前保留
- 预留安全余量（默认 1000 tokens）

**验证机制**
- 上下文大小检查
- 空消息检查
- 模型兼容性检查

---

## 模块结构

```
src/ai/
├── __init__.py          # 公开接口导出
├── types.py             # 核心类型定义
├── registry.py          # Provider 注册表
├── stream.py            # 流式事件处理
├── context.py           # 上下文管理
└── providers/
    ├── __init__.py
    └── anthropic.py     # Anthropic 实现
```

**依赖关系**
- types: 无依赖（基础层）
- stream: 依赖 types
- registry: 依赖 types, stream
- providers: 依赖 registry, 外部 SDK
- context: 依赖 types, 外部 tiktoken

---

## 扩展性设计

**添加新 Provider**
1. 实现 Provider 协议
2. 调用 register_provider()
3. 用户通过 get_provider("name") 获取

**自定义消息类型**
- 继承 Message 基类
- 在 Context 中使用
- Provider 可选择性支持

**流事件扩展**
- 新增事件类型（dataclass）
- 更新 StreamEvent Union
- 收集器自动处理未知事件

---

## 测试策略

**单元测试**
- 类型构造和序列化
- 注册表注册和获取
- Token 计算准确性

**集成测试**
- Anthropic Provider Mock
- 流事件序列验证
- 端到端对话流程

**类型检查**
- Pyright Strict Mode 全覆盖
- Protocol 实现检查
- 异步流类型推断

---

## 实施优先级

1. **types**: 所有其他模块的基础
2. **stream**: 定义事件协议
3. **registry**: Provider 管理机制
4. **anthropic**: 首个具体实现
5. **context**: 高级功能（剪枝、计算）

---

## TypeScript → Python 最佳实践

基于 pi-mono 代码分析，以下是关键语法转换要点：

### 1. 类型定义转换

**interface → Protocol/ABC**
```typescript
// TS: 对象契约
interface Provider {
  name: string;
  stream(): AsyncIterator<Event>;
}
```
```python
# Python: Protocol（结构子类型）
from typing import Protocol, runtime_checkable

@runtime_checkable
class Provider(Protocol):
    @property
    def name(self) -> str: ...
    async def stream(self) -> AsyncIterator[Event]: ...

# Python: ABC（名义子类型）
from abc import ABC, abstractmethod

class Provider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
```
**决策**: Provider 用 Protocol（灵活），抽象基类用 ABC（强制继承）

**type Union → Union/| 运算符**
```typescript
// TS: 联合类型
type Message = UserMessage | AssistantMessage | ToolResultMessage;
type Content = TextContent | ImageContent | ToolCall;
```
```python
# Python 3.10+: 使用 | 运算符
Message = UserMessage | AssistantMessage | ToolResultMessage
Content = TextContent | ImageContent | ToolCall

# Python 3.9+: 使用 Union
from typing import Union
Message = Union[UserMessage, AssistantMessage, ToolResultMessage]

# Python 3.12+: 类型别名语法
from typing import TypeAlias
Message: TypeAlias = UserMessage | AssistantMessage | ToolResultMessage
```

**可选属性 → Optional/| None**
```typescript
// TS: 可选属性
interface Context {
  systemPrompt?: string;
  temperature?: number;
  readonly apiKey?: string;
}
```
```python
# Python: Optional 或 | None
class Context(BaseModel):
    system_prompt: str | None = None
    temperature: float | None = None
    _api_key: str | None = None  # 只读用下划线前缀
```

### 2. 泛型系统转换

**泛型约束 → TypeVar + bound**
```typescript
// TS: 泛型约束
interface Tool<TParams extends Schema = Schema> {
  parameters: TParams;
}

function getModel<TApi extends Api>(api: TApi): Model<TApi>;
```
```python
# Python: TypeVar + bound
from typing import TypeVar, Generic

TParams = TypeVar("TParams", bound="Schema")
TApi = TypeVar("TApi", bound="Api")

class Tool(BaseModel, Generic[TParams]):
    parameters: TParams

def get_model(api: TApi) -> Model[TApi]: ...
```

**泛型类 → Generic[T]**
```typescript
// TS: 泛型类
class EventStream<T, R = T> implements AsyncIterable<T> {
  private queue: T[] = [];
  async *[Symbol.asyncIterator](): AsyncIterator<T> { ... }
}
```
```python
# Python: Generic[T]
from typing import Generic, TypeVar, AsyncIterator

T = TypeVar("T")
R = TypeVar("R")

class EventStream(Generic[T, R]):
    def __init__(self) -> None:
        self._queue: list[T] = []

    def __aiter__(self) -> AsyncIterator[T]:
        return self

    async def __anext__(self) -> T: ...
```

### 3. 异步模式转换

**异步生成器 → AsyncIterator**
```typescript
// TS: 异步生成器
async function* stream(): AsyncIterator<StreamEvent> {
  for await (const event of source) {
    yield convertEvent(event);
  }
}

// 消费
for await (const event of stream()) { ... }
```
```python
# Python: AsyncIterator
from typing import AsyncIterator

async def stream() -> AsyncIterator[StreamEvent]:
    async for event in source:
        yield convert_event(event)

# 消费
async for event in stream(): ...
```

**Promise → Coroutine/Task**
```typescript
// TS: Promise
async function fetch(): Promise<Response> { ... }
const result = await fetch();

// 并行执行
const results = await Promise.all([task1, task2, task3]);
```
```python
# Python: Coroutine
import asyncio
from typing import Coroutine

async def fetch() -> Response: ...
result = await fetch()

# 并行执行（推荐使用 TaskGroup Python 3.11+）
async with asyncio.TaskGroup() as tg:
    t1 = tg.create_task(task1)
    t2 = tg.create_task(task2)
results = [t1.result(), t2.result()]

# 或 asyncio.gather（兼容旧版本）
results = await asyncio.gather(task1, task2, task3)
```

### 4. 类成员转换

**访问修饰符 → 命名约定**
```typescript
// TS: 访问修饰符
class Agent {
  private _state: AgentState;           // 私有
  protected logger: Logger;              // 受保护
  public streamFn: StreamFn;             // 公开
  readonly sessionId: string;            // 只读

  get isRunning(): boolean { return this._state.isStreaming; }
}
```
```python
# Python: 命名约定 + @property
class Agent:
    def __init__(self) -> None:
        self._state: AgentState = ...           # 私有（单下划线）
        self._logger: Logger = ...              # 受保护（单下划线）
        self.stream_fn: StreamFn = ...          # 公开
        self._session_id: str = ...             # 只读（配合 @property）

    @property
    def is_running(self) -> bool:
        return self._state.is_streaming

    @property
    def session_id(self) -> str:
        return self._session_id
```

**静态属性和方法 → @staticmethod/@classmethod**
```typescript
// TS: 静态成员
class ModelRegistry {
  static instance: ModelRegistry;
  static getInstance(): ModelRegistry { ... }
}
```
```python
# Python: @staticmethod/@classmethod
class ModelRegistry:
    _instance: ClassVar[ModelRegistry | None] = None

    @classmethod
    def get_instance(cls) -> ModelRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```

### 5. 特殊语法转换

**类型守卫 → isinstance/match**
```typescript
// TS: 类型守卫（ discriminated union ）
function processEvent(event: AgentEvent) {
  switch (event.type) {
    case "message_start":
      console.log(event.message);  // TypeScript 自动收窄类型
      break;
    case "tool_execution_end":
      console.log(event.result);
      break;
  }
}
```
```python
# Python 3.10+: match（结构化匹配）
def process_event(event: AgentEvent) -> None:
    match event:
        case MessageStartEvent(message=msg):
            print(msg)
        case ToolExecutionEndEvent(result=result):
            print(result)

# Python 3.9-: isinstance + 属性检查
if isinstance(event, MessageStartEvent):
    print(event.message)
elif isinstance(event, ToolExecutionEndEvent):
    print(event.result)
```

**函数重载 → @overload**
```typescript
// TS: 函数重载
class Agent {
  async prompt(message: AgentMessage): Promise<void>;
  async prompt(input: string, images?: ImageContent[]): Promise<void>;
  async prompt(input: string | AgentMessage, images?: ImageContent[]): Promise<void> { ... }
}
```
```python
# Python: @overload
from typing import overload

class Agent:
    @overload
    async def prompt(self, message: AgentMessage) -> None: ...

    @overload
    async def prompt(self, input: str, images: list[ImageContent] | None = None) -> None: ...

    async def prompt(self, input: str | AgentMessage, images: list[ImageContent] | None = None) -> None:
        # 实现代码...
        pass
```

**常量断言 → Final/Literal**
```typescript
// TS: as const（readonly tuple）
const CLAUDE_TOOLS = ["Read", "Write", "Edit"] as const;
type ClaudeTool = typeof CLAUDE_TOOLS[number];  // "Read" | "Write" | "Edit"
```
```python
# Python: Final + Literal
from typing import Final, Literal

CLAUDE_TOOLS: Final[list[str]] = ["Read", "Write", "Edit"]
ClaudeTool = Literal["Read", "Write", "Edit"]

# 或使用枚举（推荐）
from enum import Enum, auto

class ClaudeTool(Enum):
    READ = "Read"
    WRITE = "Write"
    EDIT = "Edit"
```

**声明合并 → 基类扩展**
```typescript
// TS: Declaration Merging（接口扩展）
interface CustomAgentMessages {
  artifact: ArtifactMessage;
}
export type AgentMessage = Message | CustomAgentMessages[keyof CustomAgentMessages];
```
```python
# Python: 基类 + 继承 + Union
@runtime_checkable
class CustomMessage(Protocol):
    """自定义消息协议，应用可扩展"""
    pass

# 使用 Union 组合
AgentMessage = Message | CustomMessage

# 或注册机制（更灵活）
class MessageRegistry:
    _types: dict[str, type] = {}

    @classmethod
    def register(cls, name: str, message_type: type) -> None:
        cls._types[name] = message_type
```

### 6. 模块系统转换

**命名空间 → 包（Package）**
```typescript
// TS: 命名空间
namespace Providers {
  export class Anthropic { ... }
  export class OpenAI { ... }
}
```
```python
# Python: 包结构
# ai/providers/__init__.py
from .anthropic import AnthropicProvider
from .openai import OpenAIProvider

__all__ = ["AnthropicProvider", "OpenAIProvider"]
```

**类型导入 → TYPE_CHECKING**
```typescript
// TS: 类型导入（编译时移除）
import type { Message } from "./types.js";
import { Typebox } from "@sinclair/typebox";
```
```python
# Python: TYPE_CHECKING（运行时避免循环导入）
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import Message
    from typebox import Typebox

# 正常导入
from .utils import helper
```

### 7. Python 特有最佳实践

**dataclass vs Pydantic**
```python
# 简单数据用 dataclass（无验证需求）
from dataclasses import dataclass

@dataclass(frozen=True)  # frozen=True 对应 readonly
text: str

# 复杂数据用 Pydantic（需要验证/序列化）
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: list[Content]
    timestamp: datetime = Field(default_factory=datetime.now)
```

**上下文管理器**
```python
# 资源管理用 async contextmanager
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_stream():
    stream = await create_stream()
    try:
        yield stream
    finally:
        await stream.close()

# 使用
async with managed_stream() as stream:
    async for event in stream:
        process(event)
```

**异常处理**
```python
# 自定义异常层次
class AIError(Exception):
    """AI 模块基础异常"""
    pass

class ProviderError(AIError):
    """Provider 相关异常"""
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code

class StreamError(ProviderError):
    """流式响应异常"""
    pass
```

### 8. 关键决策清单

**必须遵守的转换规则**:
1. ✅ Protocol 用于接口定义，ABC 用于抽象基类
2. ✅ TypeVar + bound 用于泛型约束
3. ✅ `|` 运算符用于联合类型（Python 3.10+）
4. ✅ `@property` 用于只读属性
5. ✅ `_` 前缀用于私有成员（非 `__` 双下划线）
6. ✅ `@overload` 用于函数重载
7. ✅ `match` 用于类型守卫（Python 3.10+）
8. ✅ `AsyncIterator[T]` 用于异步生成器
9. ✅ `TYPE_CHECKING` 用于避免循环导入
10. ✅ Pydantic BaseModel 用于需要验证的类型

**禁止的写法**:
- ❌ 使用 `Any` 替代具体类型
- ❌ 使用 `__` 双下划线名称修饰（除非真的需要 name mangling）
- ❌ 在 Protocol 中定义具体实现
- ❌ 混合使用旧版 Union 和新的 `|` 语法
- ❌ 忽略 Pyright 的 `reportUnknownVariableType` 错误

---

## 风险与缓解

**Anthropic SDK 变更**
- 封装内部类型转换
- 限制直接使用 SDK 类型
- 监控 SDK 更新

**Token 计算不准确**
- 预留安全余量
- 提供验证方法
- 文档说明估计性质

**流式错误处理**
- 统一 Error 事件
- 客户端需处理异常
- 提供重试机制建议

**TS → Python 语义丢失**
- 严格类型检查（Pyright Strict）
- 文档说明设计决策
- Code Review 关注类型边界
