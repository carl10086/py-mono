# 文档 1：理解类型系统 (types.py)

> **目标**：掌握 Agent 模块的核心数据结构和类型定义
> 
> **预计时间**：1-2 小时
> **前置知识**：Python 类型注解、asyncio 基础

---

## 1. 为什么要先学类型？

类型是整个代码库的"词汇表"：
- 📖 **先懂词汇，再看文章** - 知道每种数据长什么样，才能理解怎么处理
- 🎯 **编译期检查** - 类型注解帮助 IDE 提供自动补全和错误检查
- 🔗 **理解关系** - 类型之间的关系反映了设计架构

---

## 2. 基础类型（第 34-43 行）

### 2.1 ToolExecutionMode

```python
type ToolExecutionMode = Literal["sequential", "parallel"]
```

**这是什么？**
控制多个工具调用的执行方式。

**两种模式对比：**

| 模式 | 执行方式 | 适用场景 | 示例 |
|------|---------|---------|------|
| `sequential` | 一个一个执行 | 工具之间有依赖 | 先查询用户ID，再查询订单 |
| `parallel` | 同时执行 | 工具相互独立 | 同时查天气、新闻、股票 |

**思考题：**
- 如果你的工具需要调用外部 API，哪种模式更快？
- 如果工具 A 的输出是工具 B 的输入，必须用哪种模式？

---

### 2.2 ThinkingLevel

```python
type ThinkingLevel = Literal["off", "minimal", "low", "medium", "high", "xhigh"]
```

**这是什么？**
控制 LLM 的"思考深度"，类似于让 LLM 在回答前"多想一会儿"。

**使用场景：**

```python
# 简单问答 - 快速回答
agent.set_thinking_level("off")
await agent.prompt("今天星期几？")

# 日常对话 - 平衡质量与速度
agent.set_thinking_level("low")
await agent.prompt("讲个笑话")

# 复杂推理 - 深度思考
agent.set_thinking_level("high")
await agent.prompt("证明勾股定理")

# 数学证明 - 极致推理
agent.set_thinking_level("xhigh")
await agent.prompt("解这个微分方程：dy/dx = y^2")
```

**注意：** 不是所有模型都支持所有等级。

---

### 2.3 StreamFn

```python
type StreamFn = Callable[
    [Model, Any, Any],
    Awaitable[Any],  # AssistantMessageEventStream
]
```

**这是什么？**
定义了如何调用 LLM 的函数签名。

**为什么重要？**
这是 Agent 和 LLM 之间的桥梁。通过自定义 `StreamFn`，你可以：
- 使用不同的 Provider（Kimi、OpenAI、Anthropic）
- 添加代理、缓存、日志
- 实现自定义路由逻辑

**典型实现：**

```python
async def my_stream_fn(model, context, options):
    """
    model: 要使用的模型
    context: 包含消息历史、系统提示、工具定义
    options: 包含 temperature、max_tokens 等参数
    
    返回: 事件流 (AssistantMessageEventStream)
    """
    provider = KimiProvider()
    return provider.stream_simple(model, context, options)

# 使用
agent = Agent(AgentOptions(stream_fn=my_stream_fn))
```

---

## 3. 工具系统（第 51-112 行）

### 3.1 AgentTool Protocol

**核心概念：**
`AgentTool` 是一个 Protocol（协议），定义了工具必须实现的接口。

**为什么要用 Protocol？**
- 不需要继承特定基类
- 任何实现了 `execute` 方法的类都可以作为工具
- Python 的鸭子类型（duck typing）

**AgentTool 的结构：**

```
AgentTool (Protocol)
├─ 属性
│   ├─ name: str              # 工具唯一标识
│   ├─ description: str       # 功能描述（给 LLM 看的）
│   ├─ parameters: dict       # JSON Schema 参数定义
│   └─ label: str            # 人类可读标签（给 UI 看的）
│
└─ 方法
    └─ execute(...)          # 执行逻辑
```

**实现一个简单工具：**

```python
class CalculatorTool:
    """计算器工具示例"""
    
    # 1. 定义元数据
    name = "calculator"
    description = "执行基础数学运算，支持加减乘除"
    label = "计算器"
    
    # 2. 定义参数（JSON Schema 格式）
    parameters = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "divide"],
                "description": "运算类型"
            },
            "a": {
                "type": "number",
                "description": "第一个数字"
            },
            "b": {
                "type": "number", 
                "description": "第二个数字"
            }
        },
        "required": ["operation", "a", "b"]
    }
    
    # 3. 实现执行逻辑
    async def execute(self, tool_call_id, params, signal, on_update):
        """
        参数说明：
        - tool_call_id: 本次调用的唯一ID，用于关联结果
        - params: 验证后的参数字典，如 {"operation": "add", "a": 1, "b": 2}
        - signal: 取消信号，长时间运行时应检查
        - on_update: 进度回调，用于长时间任务
        """
        operation = params["operation"]
        a = params["a"]
        b = params["b"]
        
        # 执行计算
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                return AgentToolResult(
                    content=[TextContent(text="错误：除数不能为0")],
                    details={"error": "DivisionByZero"}
                )
            result = a / b
        
        # 返回结果
        return AgentToolResult(
            content=[TextContent(text=f"结果是：{result}")],
            details={"operation": operation, "a": a, "b": b, "result": result}
        )
```

**注册和使用：**

```python
# 注册工具
agent.set_tools([CalculatorTool()])

# 使用
await agent.prompt("计算 15 + 27")
# LLM 会生成 tool_call: {"name": "calculator", "args": {"operation": "add", "a": 15, "b": 27}}
# Agent 调用 execute，返回结果
# LLM 生成最终回复："结果是：42"
```

---

### 3.2 AgentToolResult

```python
class AgentToolResult[TDetails]:
    content: Sequence[TextContent | ImageContent]  # 给 LLM 看的内容
    details: TDetails                              # 详细数据（任意类型）
```

**为什么分两部分？**

```
AgentToolResult
├─ content (给 LLM 看的)
│   └─ 会被加入到对话历史中
│   └─ 影响 LLM 的下一步回复
│
└─ details (给程序用的)
    └─ 不发送给 LLM
    └─ 用于日志、保存到数据库、后续处理
```

**示例：**

```python
# 天气查询工具
return AgentToolResult(
    # LLM 看到的是文本描述
    content=[TextContent(text="北京今天晴天，25°C，湿度60%")],
    
    # 程序获得结构化数据
    details={
        "city": "北京",
        "temperature": 25,
        "condition": "sunny",
        "humidity": 0.6,
        "timestamp": "2024-01-15T10:00:00Z"
    }
)
```

---

## 4. Hook 系统（第 115-203 行）

### 4.1 BeforeToolCall - 执行前拦截

**用途：**
- 权限检查
- 参数验证
- 审计日志

**示例 - 权限检查：**

```python
async def before_tool_call(ctx: BeforeToolCallContext, signal):
    """
    ctx 包含：
    - assistant_message: 请求工具的助手消息
    - tool_call: 工具调用信息（name, arguments）
    - args: 验证后的参数
    - context: 当前 Agent 上下文
    """
    
    # 检查是否是危险操作
    if ctx.tool_call.name == "delete_file":
        # 检查用户权限
        if not user_has_permission("file_write"):
            # 阻止执行
            return BeforeToolCallResult(
                block=True,
                reason="您没有删除文件的权限"
            )
    
    # 允许执行
    return None

# 注册
agent = Agent(AgentOptions(before_tool_call=before_tool_call))
```

### 4.2 AfterToolCall - 执行后处理

**用途：**
- 结果格式化
- 敏感信息过滤
- 日志记录

**示例 - 敏感信息过滤：**

```python
async def after_tool_call(ctx: AfterToolCallContext, signal):
    # 获取原始结果
    original_text = ctx.result.content[0].text
    
    # 过滤敏感信息
    filtered = original_text.replace("密码：xxx", "密码：***")
    
    # 返回修改后的结果
    return AfterToolCallResult(
        content=[TextContent(text=filtered)],
        details={**ctx.result.details, "filtered": True}
    )
```

---

## 5. 核心数据结构（第 206-361 行）

### 5.1 AgentContext vs AgentState

这是最容易混淆的两个概念：

```
AgentContext                    AgentState
(单次调用的环境)               (Agent 的运行时状态)
├─ system_prompt               ├─ system_prompt
├─ messages (会被修改)         ├─ messages (历史记录)
└─ tools                       ├─ tools
                               ├─ model
                               ├─ is_streaming
                               ├─ stream_message
                               └─ pending_tool_calls
```

**关键区别：**
- `AgentContext`：传给 Loop 的**临时环境**，Loop 会在其中添加消息
- `AgentState`：Agent 的**持久状态**，跨调用保持不变

**为什么分离？**
```python
# 每次 prompt() 都会创建新的 Context
# 但 State 是同一个对象

await agent.prompt("你好")  # 创建 Context1，修改后 State 有 2 条消息
await agent.prompt("再见")  # 创建 Context2，继承 State 的 2 条消息

# 最终 State 有 4 条消息
```

### 5.2 AgentEvent - 事件系统

**事件类型全景图：**

```
Agent 生命周期
├─ agent_start          # Agent 开始处理
└─ agent_end            # Agent 处理完成

Turn 生命周期（一次 prompt-response）
├─ turn_start          # 新的 Turn 开始
└─ turn_end            # Turn 结束

消息生命周期
├─ message_start       # 消息开始生成
├─ message_update      # 消息内容更新（流式）
└─ message_end         # 消息生成完成

工具执行
├─ tool_execution_start
└─ tool_execution_end
```

**事件格式：**

```python
# 所有事件都是字典
{
    "type": "message_end",
    "message": AssistantMessage(...)  # 具体字段取决于事件类型
}

# 订阅事件
def on_event(event):
    event_type = event.get("type")
    if event_type == "message_end":
        msg = event.get("message")
        print(f"收到消息: {msg.content[0].text}")

agent.subscribe(on_event)
```

### 5.3 AgentLoopConfig - 配置中心

**为什么需要配置对象？**

把 Loop 的所有依赖集中管理：

```python
config = AgentLoopConfig(
    model=model,                          # 使用哪个模型
    convert_to_llm=convert_fn,          # 如何转换消息
    transform_context=transform_fn,     # 如何修剪上下文
    get_api_key=key_fn,                 # 如何获取 API Key
    tool_execution="parallel",          # 工具执行模式
    before_tool_call=before_hook,       # 工具前钩子
    after_tool_call=after_hook          # 工具后钩子
)
```

**设计模式：** 依赖注入（Dependency Injection）

---

## 6. 实战练习

### 练习 1：实现 WeatherTool

要求：
1. 工具名：`get_weather`
2. 参数：city (string)
3. 返回：城市天气信息
4. 包含中文描述

<details>
<summary>参考答案</summary>

```python
class WeatherTool:
    name = "get_weather"
    description = "获取指定城市的当前天气信息，包括温度、天气状况"
    label = "天气查询"
    
    parameters = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名称，如'北京'、'上海'"
            }
        },
        "required": ["city"]
    }
    
    async def execute(self, tool_call_id, params, signal, on_update):
        city = params["city"]
        
        # 模拟查询（实际应调用天气 API）
        weather_map = {
            "北京": {"temp": 25, "condition": "晴天"},
            "上海": {"temp": 28, "condition": "多云"}
        }
        
        data = weather_map.get(city, {"temp": 20, "condition": "未知"})
        
        return AgentToolResult(
            content=[TextContent(
                text=f"{city}今天{data['condition']}，{data['temp']}°C"
            )],
            details={"city": city, **data}
        )
```

</details>

### 练习 2：理解事件流

在下面的代码中标注每个事件的触发时机：

```python
await agent.prompt("你好")
await agent.wait_for_idle()
```

<details>
<summary>答案</summary>

```
await agent.prompt("你好")
    │
    ├─ [agent_start]          # Agent 开始处理
    ├─ [turn_start]           # 新的 Turn
    ├─ [message_start]        # UserMessage "你好"
    ├─ [message_end]          # UserMessage 结束
    │
    ├─ 调用 LLM...
    │
    ├─ [message_start]        # AssistantMessage 开始生成
    ├─ [message_update] × N   # 流式输出
    ├─ [message_end]          # AssistantMessage 完成
    ├─ [turn_end]             # Turn 结束
    └─ [agent_end]            # Agent 处理完成
```

</details>

---

## 7. 常见问题

**Q1: ToolExecutionMode 和 ThinkingLevel 有什么区别？**

- `ToolExecutionMode`：控制**多个工具**如何执行（顺序/并行）
- `ThinkingLevel`：控制 LLM 的**推理深度**

**Q2: 为什么 AgentTool 是 Protocol 而不是抽象类？**

- Protocol 支持鸭子类型，不需要显式继承
- 更灵活，已有类只需实现 execute 方法即可
- 符合 Python 的 "如果它走起来像鸭子..." 哲学

**Q3: AgentContext 和 AgentState 的消息列表是同一个对象吗？**

- 不是！Context 创建时复制 State 的消息：`list(context.messages)`
- Loop 修改 Context 的消息，然后通过事件通知 Agent
- Agent 在 `_process_loop_event` 中更新自己的 State

---

## 8. 下一步

完成本文档后，你应该能：
- ✅ 理解所有基础类型的含义
- ✅ 实现一个简单的 AgentTool
- ✅ 理解事件系统的运作方式
- ✅ 区分 Context 和 State

**下一步：** [文档 2：Agent 基础用法](02_agent_basics.md)

---

## 附录：类型关系图

```
AgentOptions
    ├─ initial_state: AgentState
    ├─ stream_fn: StreamFn
    ├─ convert_to_llm: Callable
    ├─ tool_execution: ToolExecutionMode
    └─ before/after_tool_call: Hook

Agent
    ├─ _state: AgentState
    ├─ _listeners: Set[Callable]
    ├─ _steering_queue: List[AgentMessage]
    └─ _follow_up_queue: List[AgentMessage]

AgentState
    ├─ messages: List[AgentMessage]
    ├─ tools: List[AgentTool]
    └─ model: Model

AgentContext (单次调用)
    ├─ system_prompt: str
    ├─ messages: List[AgentMessage]  (会被修改)
    └─ tools: Optional[List[AgentTool]]

AgentEvent (字典)
    └─ type: str
       ├─ "agent_start/end"
       ├─ "turn_start/end"
       ├─ "message_start/update/end"
       └─ "tool_execution_start/end"
```
