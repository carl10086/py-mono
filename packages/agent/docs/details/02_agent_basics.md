# 文档 2：Agent 基础用法 (agent.py)

> **目标**：掌握 Agent 类的核心用法和配置
> 
> **预计时间**：2-3 小时
> **前置知识**：文档 1 的内容，asyncio 基础

---

## 1. 创建第一个 Agent

### 1.1 最简单的 Agent

```python
import asyncio
from ai.providers import KimiProvider
from agent import Agent, AgentOptions

async def main():
    # 1. 创建 Provider
    provider = KimiProvider()
    
    # 2. 定义流式函数（这是必须的！）
    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)
    
    # 3. 创建 Agent
    agent = Agent(AgentOptions(stream_fn=stream_fn))
    agent.set_model(provider.get_model())
    agent.set_system_prompt("你是一个有帮助的助手")
    
    # 4. 发送消息
    await agent.prompt("你好！请介绍一下 Python")
    await agent.wait_for_idle()
    
    # 5. 查看结果
    print(f"对话历史: {len(agent.state.messages)} 条消息")

asyncio.run(main())
```

**为什么需要 `stream_fn`？**

```
Agent 本身不知道如何调用 LLM
        ↓
stream_fn 是 Agent 和 LLM 之间的桥梁
        ↓
通过 stream_fn，Agent 可以获得流式事件
        ↓
Agent 解析事件并发射给用户
```

---

## 2. 理解执行流程

### 2.1 prompt() 的内部流程

当你调用 `await agent.prompt("你好")` 时，发生了什么？

```
┌─────────────────────────────────────────────────────────┐
│ 1. 参数检查                                               │
│    - 检查 is_streaming，如果为 True 抛出异常               │
│    - 检查 model 是否已配置                                 │
└────────────────────┬──────────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────────┐
│ 2. 参数转换                                               │
│    - str → UserMessage                                    │
│    - 如果有 images，创建 ImageContent                      │
│    - 最终得到 List[AgentMessage]                          │
└────────────────────┬──────────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────────┐
│ 3. 调用 _run_loop()                                       │
│    - 设置 is_streaming = True                             │
│    - 构建 AgentContext                                    │
│    - 调用 run_agent_loop()                                │
└────────────────────┬──────────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────────┐
│ 4. Loop 执行（异步）                                       │
│    - 发射 agent_start 事件                                │
│    - 调用 LLM                                             │
│    - 处理流式响应                                          │
│    - 发射各种事件                                          │
│    - 发射 agent_end 事件                                  │
└────────────────────┬──────────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────────┐
│ 5. prompt() 立即返回                                       │
│    - 注意：此时 LLM 可能还在生成！                          │
│    - 需要调用 wait_for_idle() 等待完成                     │
└───────────────────────────────────────────────────────────┘
```

### 2.2 为什么 prompt() 不等待完成？

**关键设计：异步非阻塞**

```python
# prompt() 立即返回，不等待 LLM 生成完成
await agent.prompt("你好")  # ← 立即返回

# 此时可以做其他事情，比如更新 UI
update_ui("正在思考...")

# 等待完成
await agent.wait_for_idle()  # ← 真正等待 LLM 完成

# 现在可以安全地读取结果
print(agent.state.messages[-1].content[0].text)
```

**好处：**
- UI 不会被阻塞
- 可以并发处理多个任务
- 可以中途取消或干预

---

## 3. 事件订阅详解

### 3.1 基础用法

```python
def on_event(event):
    """处理 Agent 事件"""
    event_type = event.get("type")
    
    if event_type == "message_start":
        print("📝 开始生成消息")
        
    elif event_type == "message_update":
        # 流式输出
        msg = event.get("message")
        if msg and msg.content:
            text = msg.content[0].text
            print(f"收到: {text[-20:]}")  # 打印最后 20 个字符
            
    elif event_type == "message_end":
        print("✅ 消息生成完成")
        
    elif event_type == "agent_end":
        print("🏁 Agent 处理完成")

# 订阅
unsubscribe = agent.subscribe(on_event)

# 使用...
await agent.prompt("你好")
await agent.wait_for_idle()

# 取消订阅
unsubscribe()
```

### 3.2 实现打字机效果

```python
import sys

def create_typewriter_callback():
    """创建打字机效果的回调"""
    current_text = ""
    
    def on_event(event):
        nonlocal current_text
        
        event_type = event.get("type")
        
        if event_type == "message_start":
            print("助手: ", end="", flush=True)
            current_text = ""
            
        elif event_type == "message_update":
            msg = event.get("message")
            if msg and msg.content:
                new_text = msg.content[0].text
                # 只打印新增的部分
                added = new_text[len(current_text):]
                print(added, end="", flush=True)
                current_text = new_text
                
        elif event_type == "message_end":
            print()  # 换行
            
    return on_event

agent.subscribe(create_typewriter_callback())
await agent.prompt("讲个故事")
await agent.wait_for_idle()
```

### 3.3 事件统计

```python
event_counts = {}

def on_event(event):
    event_type = event.get("type", "unknown")
    event_counts[event_type] = event_counts.get(event_type, 0) + 1

agent.subscribe(on_event)

await agent.prompt("你好")
await agent.wait_for_idle()

print("事件统计:")
for event_type, count in sorted(event_counts.items()):
    print(f"  {event_type}: {count}")
```

**典型输出：**
```
事件统计:
  agent_end: 1
  agent_start: 1
  message_end: 2
  message_start: 2
  message_update: 156
  turn_end: 1
  turn_start: 1
```

---

## 4. 配置选项详解

### 4.1 AgentOptions 全览

```python
from agent import AgentOptions

options = AgentOptions(
    # 1. 流式函数（必须）
    stream_fn=stream_fn,
    
    # 2. 初始状态（可选，用于恢复会话）
    initial_state=None,
    
    # 3. 消息处理
    convert_to_llm=None,      # 自定义消息转换
    transform_context=None,   # 上下文转换（如修剪）
    
    # 4. 队列模式
    steering_mode="one-at-a-time",  # "all" 或 "one-at-a-time"
    follow_up_mode="one-at-a-time",
    
    # 5. 工具执行
    tool_execution="parallel",  # "sequential" 或 "parallel"
    before_tool_call=None,      # 工具前钩子
    after_tool_call=None,       # 工具后钩子
    
    # 6. 认证
    get_api_key=None,  # 动态获取 API Key
    
    # 7. 其他
    session_id=None,
    thinking_budgets=None,
    transport="sse",
    max_retry_delay_ms=None,
)
```

### 4.2 消息转换示例

**场景：只保留最近 10 条消息**

```python
async def convert_to_llm(messages):
    """只保留最近 10 条消息"""
    return messages[-10:]

agent = Agent(AgentOptions(
    stream_fn=stream_fn,
    convert_to_llm=convert_to_llm
))
```

**场景：过滤特定角色**

```python
async def convert_to_llm(messages):
    """只保留 user 和 assistant 消息"""
    return [
        m for m in messages 
        if m.role in ["user", "assistant"]
    ]
```

### 4.3 上下文修剪

**场景：Token 数超过限制时删除旧消息**

```python
def count_tokens(messages):
    """简单估算 Token 数"""
    total = 0
    for m in messages:
        if hasattr(m, 'content') and m.content:
            for c in m.content:
                if hasattr(c, 'text'):
                    # 粗略估算：1 个中文字 ≈ 1.5 个 token
                    total += len(c.text) * 1.5
    return int(total)

async def prune_context(messages, signal):
    """上下文修剪策略"""
    MAX_TOKENS = 4000
    
    while count_tokens(messages) > MAX_TOKENS and len(messages) > 2:
        # 删除最旧的消息（保留 system prompt）
        messages.pop(0)
    
    return messages

agent = Agent(AgentOptions(
    stream_fn=stream_fn,
    transform_context=prune_context
))
```

---

## 5. 状态管理

### 5.1 保存和恢复对话

```python
import json
from agent.types import AgentState

def save_conversation(agent, filepath):
    """保存对话到文件"""
    state = agent.state
    
    # 序列化（简化版，实际需要更完整的序列化）
    data = {
        "system_prompt": state.system_prompt,
        "thinking_level": state.thinking_level,
        "messages": [
            {
                "role": msg.role,
                "content": [
                    {"type": c.type, "text": c.text}
                    for c in msg.content
                ]
            }
            for msg in state.messages
        ]
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_conversation(filepath):
    """从文件加载对话"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 重建消息列表
    from ai.types import UserMessage, AssistantMessage, TextContent
    
    messages = []
    for msg_data in data["messages"]:
        content = [
            TextContent(text=c["text"])
            for c in msg_data["content"]
        ]
        
        if msg_data["role"] == "user":
            messages.append(UserMessage(content=content))
        else:
            messages.append(AssistantMessage(content=content))
    
    # 创建 State
    state = AgentState(
        system_prompt=data["system_prompt"],
        thinking_level=data["thinking_level"],
        messages=messages
    )
    
    return state

# 使用
save_conversation(agent, "chat_001.json")

# 稍后恢复
loaded_state = load_conversation("chat_001.json")
agent = Agent(AgentOptions(
    stream_fn=stream_fn,
    initial_state=loaded_state
))
agent.set_model(model)
```

### 5.2 状态检查

```python
# 检查是否在生成中
if agent.state.is_streaming:
    print("Agent 正在处理中，请稍候...")
else:
    print("Agent 空闲，可以发送消息")

# 查看对话长度
print(f"已进行 {len(agent.state.messages)} 轮对话")

# 检查待执行的工具
if agent.state.pending_tool_calls:
    print(f"有 {len(agent.state.pending_tool_calls)} 个工具在执行中")

# 检查错误
if agent.state.error:
    print(f"上次执行出错: {agent.state.error}")
```

### 5.3 重置状态

```python
# 完全重置（清空消息，保留配置）
agent.reset()
print(f"消息数: {len(agent.state.messages)}")  # 0

# 只清空消息列表
agent.clear_messages()

# 替换消息历史
agent.replace_messages(new_messages)
```

---

## 6. 实战练习

### 练习 1：实现 Token 计数器

在事件回调中统计生成的 Token 数（按字符估算）。

<details>
<summary>提示</summary>

使用 `message_update` 事件，比较新旧文本的长度差。

</details>

### 练习 2：实现对话导出

实现一个函数，将对话导出为 Markdown 格式。

<details>
<summary>参考答案</summary>

```python
def export_to_markdown(agent, filepath):
    lines = ["# 对话记录\n"]
    
    for msg in agent.state.messages:
        role = "用户" if msg.role == "user" else "助手"
        lines.append(f"## {role}\n")
        
        for content in msg.content:
            if content.type == "text":
                lines.append(f"{content.text}\n")
            elif content.type == "toolCall":
                lines.append(f"*[工具调用: {content.name}]*\n")
        
        lines.append("\n---\n")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
```

</details>

### 练习 3：实现对话长度限制

当对话超过 20 条消息时，自动提醒用户。

<details>
<summary>参考答案</summary>

```python
def create_length_limit_callback(max_messages=20):
    warned = False
    
    def on_event(event):
        nonlocal warned
        
        if event.get("type") == "agent_end":
            msg_count = len(agent.state.messages)
            
            if msg_count >= max_messages and not warned:
                print(f"⚠️  提醒：对话已有 {msg_count} 条消息，建议新建对话")
                warned = True
    
    return on_event

agent.subscribe(create_length_limit_callback(20))
```

</details>

---

## 7. 常见问题

**Q1: prompt() 和 wait_for_idle() 有什么区别？**

- `prompt()`：发送消息给 Agent，**立即返回**
- `wait_for_idle()`：等待 Agent 处理完成，**阻塞直到完成**

类比：
```
prompt() = 寄出一封信（不等待回复）
wait_for_idle() = 等待回信到达
```

**Q2: 为什么需要 subscribe()？不能直接获取结果吗？**

因为 LLM 生成是**流式**的，结果逐步产生。subscribe 可以：
- 实时显示生成内容（打字机效果）
- 监控执行状态
- 在生成过程中干预（如 steering）

**Q3: AgentOptions 的哪些配置最常用？**

必配：
- `stream_fn`：连接 LLM（必须）

常用：
- `tool_execution`：控制工具执行模式
- `before_tool_call`：权限检查
- `convert_to_llm`：自定义消息处理

进阶：
- `transform_context`：上下文修剪
- `get_api_key`：动态认证

**Q4: 如何知道 Agent 是否空闲？**

```python
if agent.state.is_streaming:
    print("忙碌中")
else:
    print("空闲")
```

---

## 8. 下一步

完成本文档后，你应该能：
- ✅ 创建和配置 Agent
- ✅ 理解异步执行流程
- ✅ 使用事件系统
- ✅ 管理 Agent 状态

**下一步：** [文档 3：多轮对话与记忆](03_conversation_and_memory.md)

---

## 附录：Agent 类核心方法速查

| 方法 | 用途 | 是否异步 |
|------|------|---------|
| `prompt()` | 发送消息 | ✅ |
| `wait_for_idle()` | 等待完成 | ✅ |
| `subscribe()` | 订阅事件 | ❌ |
| `steer()` | 插入 steering | ❌ |
| `follow_up()` | 插入 follow-up | ❌ |
| `reset()` | 重置状态 | ❌ |
| `set_model()` | 设置模型 | ❌ |
| `set_system_prompt()` | 设置系统提示 | ❌ |
| `set_tools()` | 设置工具 | ❌ |
| `set_thinking_level()` | 设置思考等级 | ❌ |
| `clear_messages()` | 清空消息 | ❌ |
| `replace_messages()` | 替换消息 | ❌ |
