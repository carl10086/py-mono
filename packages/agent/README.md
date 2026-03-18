# Agent 运行时

一个高层次的 LLM Agent 运行时框架，提供对话管理、工具调用、事件订阅等核心功能。

## 目录

- [设计理念](#设计理念)
- [架构设计](#架构设计)
- [核心概念](#核心概念)
- [快速开始](#快速开始)
- [详细使用指南](#详细使用指南)
- [API 参考](#api-参考)
- [Examples](#examples)

---

## 设计理念

### 为什么需要 Agent 运行时？

直接调用 LLM API 只能得到单次回复，而 Agent 需要：

1. **对话历史管理** - 维护上下文，支持多轮对话
2. **工具调用** - 让 LLM 调用外部函数获取信息或执行操作
3. **流式响应** - 实时显示生成内容，提升用户体验
4. **事件系统** - 可观测的执行过程，支持 UI 更新和日志记录
5. **消息队列** - 支持用户打断、系统干预等复杂交互

### 设计原则

- **简单直观**: 10 行代码即可开始对话
- **高度可扩展**: 通过 Hook 和配置自定义行为
- **事件驱动**: 完整的事件系统，支持实时监控
- **类型安全**: 完整的类型注解，IDE 友好

---

## 架构设计

### 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                         用户代码                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ prompt()    │  │ subscribe()  │  │ set_tools()      │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                      Agent 类                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 职责：                                                │  │
│  │ - 状态管理（对话历史、系统提示）                       │  │
│  │ - 事件订阅/发布                                       │  │
│  │ - 消息队列（steering/follow-up）                      │  │
│  │ - 生命周期管理                                        │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    Agent Loop                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 职责：                                                │  │
│  │ - 协调 LLM 调用                                       │  │
│  │ - 处理流式响应                                        │  │
│  │ - 发射事件                                            │  │
│  │ - 管理消息生命周期                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   AI Stream (py-mono-ai)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 职责：                                                │  │
│  │ - 多 Provider 支持（Kimi、OpenAI、Anthropic）         │  │
│  │ - 流式事件生成（text_delta、tool_call 等）            │  │
│  │ - 消息格式转换                                        │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    LLM Provider                             │
│                (Kimi / OpenAI / Anthropic)                  │
└─────────────────────────────────────────────────────────────┘
```

### 执行流程

```
用户调用 prompt("你好")
         │
         ▼
┌─────────────────┐
│   Agent.prompt  │
│  - 参数转换     │
│  - 启动 Loop    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  run_agent_loop │
│  - 构建上下文   │
│  - 发射事件     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  _stream_resp   │────▶│  LLM 流式响应   │
│  - 调用 LLM     │     │  - text_delta   │
│  - 解析事件     │     │  - tool_call    │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│  事件发射       │
│  - message_start│
│  - message_upd  │
│  - message_end  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 订阅者回调      │
│ - UI 更新       │
│ - 日志记录      │
└─────────────────┘
```

### 状态流转

```
初始状态
    │
    ▼ set_model(), set_system_prompt()
配置完成
    │
    ▼ prompt()
正在生成 (is_streaming=True)
    │
    ├── message_start ──▶ 流式输出
    │        │
    │        ├── text_delta × N
    │        │
    │        └── message_end
    │
    ▼
空闲 (is_streaming=False)
    │
    ◄────── 用户发送新消息
```

---

## 核心概念

### 1. 状态管理 (AgentState)

Agent 维护完整的运行时状态：

```python
class AgentState:
    system_prompt: str          # 系统提示
    model: Model               # 当前模型
    messages: list[Message]    # 对话历史
    tools: list[AgentTool]     # 可用工具
    is_streaming: bool         # 是否正在生成
    pending_tool_calls: set    # 待执行的工具调用
```

**对话历史的持久化**:
```python
# 保存状态
saved_state = agent.state

# 恢复状态（跨会话）
agent = Agent(AgentOptions(initial_state=saved_state))
```

### 2. 事件系统

通过事件系统实现可观测性：

```
Agent 生命周期：
  agent_start ────────▶ agent_end

Turn 生命周期：
  turn_start ────────▶ turn_end

消息生命周期：
  message_start ──▶ message_update × N ──▶ message_end

工具执行：
  tool_exec_start ──▶ tool_exec_end
```

**订阅事件**:
```python
def on_event(event):
    event_type = event.get("type")
    if event_type == "message_end":
        message = event.get("message")
        print(f"收到: {message.content[0].text}")

unsubscribe = agent.subscribe(on_event)
```

### 3. 消息队列

#### Steering 队列（高优先级）

用于用户打断、系统干预：

```python
# 用户正在询问复杂问题
await agent.prompt("详细解释量子力学")

# 用户改变主意，打断当前生成
agent.steer(UserMessage(text="不用详细了，一句话总结"))
```

**执行顺序**：
```
prompt("解释量子力学")
    │
    ├── LLM 开始生成...
    │
    ├── steer("一句话总结")  ◄── 插入 steering
    │
    └── 处理 steering 消息，停止原生成
```

#### Follow-up 队列（低优先级）

用于自动追问、任务链：

```python
# 在回调中添加 follow-up
def on_event(event):
    if event.get("type") == "agent_end":
        # 任务完成，自动追问
        agent.follow_up(UserMessage(text="还有其他问题吗？"))
```

### 4. 工具调用

Agent 支持可插拔的工具系统：

```python
class WeatherTool:
    name = "get_weather"
    description = "获取指定城市的天气"
    parameters = {
        "type": "object",
        "properties": {
            "city": {"type": "string"}
        },
        "required": ["city"]
    }
    
    async def execute(self, tool_call_id, params, signal, on_update):
        city = params["city"]
        weather = await fetch_weather(city)
        return AgentToolResult(
            content=[TextContent(text=f"{city}天气：{weather}")],
            details={"city": city, "weather": weather}
        )

# 注册工具
agent.set_tools([WeatherTool()])
```

**工具调用流程**:
```
用户：北京天气怎么样？
    │
    ▼
LLM 生成 tool_call: {"name": "get_weather", "args": {"city": "北京"}}
    │
    ▼
Agent 查找 WeatherTool
    │
    ▼
执行 tool.execute()
    │
    ▼
生成 toolResult 消息
    │
    ▼
LLM 生成最终回复："北京今天晴朗，25°C"
```

---

## 快速开始

### 1. 基础对话

```python
import asyncio
from ai.providers import KimiProvider
from agent import Agent, AgentOptions

async def main():
    # 创建 Provider
    provider = KimiProvider()
    
    # 定义流式函数
    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)
    
    # 创建 Agent
    agent = Agent(AgentOptions(stream_fn=stream_fn))
    agent.set_model(provider.get_model())
    agent.set_system_prompt("你是一个有帮助的助手")
    
    # 订阅事件（可选）
    agent.subscribe(lambda e: print(f"[{e.get('type')}]") 
                   if e.get('type') in ['message_start', 'message_end'] 
                   else None)
    
    # 发送消息
    await agent.prompt("你好！请介绍一下 Python 的优点")
    await agent.wait_for_idle()
    
    print(f"\n对话历史: {len(agent.state.messages)} 条消息")

asyncio.run(main())
```

**输出**:
```
[message_start]
[message_end]

对话历史: 2 条消息
```

### 2. 多轮对话

```python
# 第一轮
await agent.prompt("你好，我叫小明")
await agent.wait_for_idle()

# 第二轮（Agent 记得上下文）
await agent.prompt("我叫什么名字？")
await agent.wait_for_idle()
# 输出："你叫小明"

# 查看完整对话
for msg in agent.state.messages:
    print(f"{msg.role}: {msg.content[0].text}")
```

### 3. 带工具的对话

```python
# 定义工具
class FileReadTool:
    name = "read_file"
    description = "读取文件内容"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"}
        },
        "required": ["path"]
    }
    
    async def execute(self, tool_call_id, params, signal, on_update):
        path = params["path"]
        try:
            content = Path(path).read_text()
            return AgentToolResult(
                content=[TextContent(text=content)],
                details={"path": path, "size": len(content)}
            )
        except FileNotFoundError:
            return AgentToolResult(
                content=[TextContent(text=f"文件不存在: {path}")],
                details={"error": "FileNotFound"}
            )

# 注册工具
agent.set_tools([FileReadTool()])

# 使用工具
await agent.prompt("读取 README.md 并总结")
await agent.wait_for_idle()
```

---

## 详细使用指南

### 配置选项 (AgentOptions)

```python
from agent import AgentOptions

options = AgentOptions(
    # 流式调用函数
    stream_fn=custom_stream,
    
    # 消息转换
    convert_to_llm=lambda msgs: msgs[-10:],  # 只保留最近 10 条
    
    # 上下文转换（上下文修剪）
    transform_context=prune_context,
    
    # 队列模式
    steering_mode="one-at-a-time",  # 或 "all"
    follow_up_mode="one-at-a-time",  # 或 "all"
    
    # 工具执行模式
    tool_execution="parallel",  # 或 "sequential"
    
    # 工具钩子
    before_tool_call=permission_check,
    after_tool_call=log_tool_call,
    
    # 动态 API Key（用于 OAuth）
    get_api_key=lambda provider: get_oauth_token(),
)

agent = Agent(options)
```

### 状态管理

```python
# 保存状态
saved_state = agent.state
save_to_disk(saved_state, "session.json")

# 恢复状态
loaded_state = load_from_disk("session.json")
agent = Agent(AgentOptions(initial_state=loaded_state))

# 重置状态
agent.reset()  # 清空消息历史，保留配置

# 清空消息
agent.clear_messages()

# 替换消息历史
agent.replace_messages(new_history)
```

### 高级事件处理

```python
def on_event(event):
    event_type = event.get("type")
    
    if event_type == "message_start":
        print("助手开始回复...")
        
    elif event_type == "message_update":
        # 流式更新
        msg = event.get("message")
        if msg and msg.content:
            for content in msg.content:
                if content.type == "text":
                    print(content.text, end="", flush=True)
                    
    elif event_type == "message_end":
        print("\n回复完成")
        
    elif event_type == "tool_execution_start":
        print(f"执行工具: {event.get('toolName')}")
        
    elif event_type == "agent_end":
        print(f"Agent 处理完成，共 {len(agent.state.messages)} 条消息")

# 订阅并保存取消函数
unsubscribe = agent.subscribe(on_event)

# 取消订阅
unsubscribe()
```

### Steering 使用

```python
# 场景：用户改变主意
async def handle_user_input(user_text):
    if user_text.startswith("/stop"):
        # 用户打断当前生成
        agent.steer(UserMessage(text="停止生成"))
    else:
        await agent.prompt(user_text)
    
    await agent.wait_for_idle()
```

### 思考模式

```python
# 启用思考模式
agent.set_thinking_level("high")

# 不同场景使用不同等级
agent.set_thinking_level("off")      # 简单问答
agent.set_thinking_level("medium")   # 一般任务
agent.set_thinking_level("high")     # 复杂推理
agent.set_thinking_level("xhigh")    # 数学证明、代码调试
```

---

## API 参考

### Agent 类

#### 构造函数

```python
Agent(opts: AgentOptions | None)
```

#### 主要方法

| 方法 | 说明 | 示例 |
|------|------|------|
| `prompt(input, images)` | 发送提示 | `await agent.prompt("你好")` |
| `wait_for_idle()` | 等待完成 | `await agent.wait_for_idle()` |
| `subscribe(fn)` | 订阅事件 | `agent.subscribe(on_event)` |
| `steer(msg)` | 插入 steering | `agent.steer(UserMessage(...))` |
| `follow_up(msg)` | 插入 follow-up | `agent.follow_up(UserMessage(...))` |
| `reset()` | 重置状态 | `agent.reset()` |
| `set_model(m)` | 设置模型 | `agent.set_model(model)` |
| `set_system_prompt(s)` | 设置系统提示 | `agent.set_system_prompt("...")` |
| `set_tools(tools)` | 设置工具 | `agent.set_tools([...])` |
| `set_thinking_level(l)` | 设置思考等级 | `agent.set_thinking_level("high")` |

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `state` | AgentState | 当前状态（只读） |
| `session_id` | str \| None | 会话 ID |
| `tool_execution` | ToolExecutionMode | 工具执行模式 |

### AgentOptions

```python
AgentOptions(
    initial_state: AgentState | None = None,
    stream_fn: StreamFn | None = None,
    convert_to_llm: Callable | None = None,
    transform_context: Callable | None = None,
    steering_mode: "all" | "one-at-a-time" = "one-at-a-time",
    follow_up_mode: "all" | "one-at-a-time" = "one-at-a-time",
    tool_execution: "sequential" | "parallel" = "parallel",
    before_tool_call: BeforeToolCallHook | None = None,
    after_tool_call: AfterToolCallHook | None = None,
    get_api_key: Callable | None = None,
    thinking_budgets: ThinkingBudgets | None = None,
)
```

### 事件类型

```python
# Agent 生命周期
{"type": "agent_start"}
{"type": "agent_end", "messages": [...]}

# Turn 生命周期
{"type": "turn_start"}
{"type": "turn_end", "message": AssistantMessage, "toolResults": [...]}

# 消息生命周期
{"type": "message_start", "message": AgentMessage}
{"type": "message_update", "message": AgentMessage, "assistantMessageEvent": Event}
{"type": "message_end", "message": AgentMessage}

# 工具执行
{"type": "tool_execution_start", "toolCallId": str, "toolName": str, "args": dict}
{"type": "tool_execution_end", "toolCallId": str, "result": AgentToolResult, "isError": bool}
```

---

## Examples

查看 `examples/` 目录：

```bash
cd packages/agent

# 基础使用
uv run python examples/01_basic_agent.py

# 事件监听
uv run python examples/02_agent_events.py

# 多轮对话（记忆测试）
uv run python examples/03_conversation.py

# Steering 功能
uv run python examples/04_steering.py

# 状态管理
uv run python examples/05_state_management.py

# 思考模式
uv run python examples/06_thinking_mode.py
```

### 运行测试

```bash
# 所有 examples
for f in examples/*.py; do
    echo "Running $f..."
    uv run python "$f"
done
```

---

## 设计对比

### 与 pi-mono 的关系

本实现对标 pi-mono 的 Agent 模块，主要差异：

| 特性 | pi-mono (TypeScript) | py-mono (Python) |
|------|---------------------|------------------|
| 语言 | TypeScript | Python 3.12+ |
| 流式处理 | 异步迭代器 | 异步迭代器 |
| 类型系统 | TypeScript 类型 | Python type hints |
| 包结构 | coding-agent + agent | 合并为 agent |
| 工具实现 | coding-agent/tools/ | agent/tools/ |

### 设计决策

1. **合并 coding-agent**: 简化起步，无需完整 CLI
2. **字典事件**: Python 中字典比类更灵活，保持与 pi-mono 的兼容性
3. **类型别名**: 大量使用 type alias 提高可读性
4. **中文注释**: 团队主要使用中文，文档和注释用中文编写

---

## 路线图

- [x] 基础对话功能
- [x] 多轮对话（记忆）
- [x] 事件系统
- [x] Steering/Follow-up 队列
- [x] 工具调用框架
- [ ] 内置工具实现（bash、read、write、edit）
- [ ] 上下文修剪策略
- [ ] 多 Agent 协作
- [ ] 持久化存储

---

## 贡献

欢迎提交 Issue 和 PR！

代码规范：
- 函数长度 ≤ 30 行
- 类型注解完整
- 中文文档字符串
- 通过 ruff + pyright 检查

---

## License

MIT
