# 文档 3：多轮对话与记忆

> **目标**：理解 Agent 如何维护对话历史和上下文
> 
> **预计时间**：2-3 小时
> **前置知识**：文档 1-2 的内容

---

## 1. 对话历史的本质

### 1.1 消息列表的结构

```python
agent.state.messages  # List[AgentMessage]

# 典型的对话历史：
[
    UserMessage(text="你好，我叫小明"),           # 用户第 1 轮
    AssistantMessage(text="你好小明！很高兴认识你"),  # 助手第 1 轮
    UserMessage(text="我叫什么名字？"),           # 用户第 2 轮
    AssistantMessage(text="你叫小明"),           # 助手第 2 轮
    UserMessage(text="请总结对话"),              # 用户第 3 轮
    AssistantMessage(text="小明问我他叫什么名字...")  # 助手第 3 轮
]
```

**关键理解：**
- Agent 不"记住"任何东西，它只是把历史消息发给 LLM
- LLM 根据完整的历史生成回复
- 这就是多轮对话能工作的原理

### 1.2 上下文传递流程

```
用户调用 prompt("你好")
        │
        ▼
┌──────────────────────────────────────┐
│ 1. Agent 获取当前 messages            │
│    (已有历史: [Msg1, Msg2, ...])      │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 2. 添加新消息                         │
│    messages.append(UserMessage("你好"))│
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 3. 发送给 LLM                         │
│    LLM 看到完整历史，生成回复          │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 4. 添加助手回复到历史                 │
│    messages.append(AssistantMessage(...))│
└──────────────────────────────────────┘
```

---

## 2. 多轮对话示例

### 2.1 基础多轮对话

```python
async def multi_turn_conversation():
    # 第 1 轮
    await agent.prompt("你好，我叫小明，今年 25 岁")
    await agent.wait_for_idle()
    # messages: [User, Assistant]
    
    # 第 2 轮 - Agent 记得"小明"
    await agent.prompt("我叫什么名字？")
    await agent.wait_for_idle()
    # Agent 回复："你叫小明"
    # messages: [User, Assistant, User, Assistant]
    
    # 第 3 轮 - Agent 记得"25 岁"
    await agent.prompt("我今年多大了？")
    await agent.wait_for_idle()
    # Agent 回复："你今年 25 岁"
    
    # 第 4 轮 - Agent 能综合信息
    await agent.prompt("用一句话介绍我")
    await agent.wait_for_idle()
    # Agent 回复："你叫小明，今年 25 岁"
```

**为什么会"记得"？**

每次调用 `prompt()` 时，Agent 会把**完整的历史**发给 LLM：

```
发送给 LLM 的上下文：

System: 你是一个有帮助的助手

User: 你好，我叫小明，今年 25 岁
Assistant: 你好小明！很高兴认识你

User: 我叫什么名字？
Assistant: 你叫小明

User: 我今年多大了？
Assistant: 你今年 25 岁

User: 用一句话介绍我    ← 当前问题
Assistant: ?             ← LLM 生成回答
```

### 2.2 查看对话历史

```python
async def inspect_conversation():
    await agent.prompt("你好，我叫小明")
    await agent.wait_for_idle()
    
    await agent.prompt("我叫什么名字？")
    await agent.wait_for_idle()
    
    # 打印完整对话
    print("=== 对话历史 ===")
    for i, msg in enumerate(agent.state.messages, 1):
        role = "用户" if msg.role == "user" else "助手"
        text = msg.content[0].text
        print(f"{i}. {role}: {text[:50]}...")
```

**输出：**
```
=== 对话历史 ===
1. 用户: 你好，我叫小明...
2. 助手: 你好小明！很高兴认识你...
3. 用户: 我叫什么名字？...
4. 助手: 你叫小明...
```

---

## 3. 上下文长度限制

### 3.1 为什么会有长度限制？

- **LLM 有最大 Token 限制**（如 4K, 8K, 32K, 128K）
- **过长的上下文**：
  - 增加 API 调用成本
  - 降低响应速度
  - 可能导致性能下降

### 3.2 估算 Token 数

```python
def estimate_tokens(text: str) -> int:
    """
    粗略估算 Token 数
    中文：1 字 ≈ 1.5 tokens
    英文：1 词 ≈ 1.3 tokens
    """
    # 简单估算：每字符约 1.5 tokens（中文）
    return int(len(text) * 1.5)

def count_messages_tokens(messages) -> int:
    """计算消息列表的 Token 数"""
    total = 0
    for msg in messages:
        if hasattr(msg, 'content') and msg.content:
            for content in msg.content:
                if hasattr(content, 'text'):
                    total += estimate_tokens(content.text)
    return total

# 使用
print(f"当前对话约 {count_messages_tokens(agent.state.messages)} tokens")
```

### 3.3 上下文修剪策略

**策略 1：滑动窗口（只保留最近 N 条）**

```python
async def sliding_window(messages, signal):
    """只保留最近 10 条消息"""
    return messages[-10:]

agent = Agent(AgentOptions(
    stream_fn=stream_fn,
    transform_context=sliding_window
))
```

**策略 2：Token 阈值（超过则删除旧消息）**

```python
async def token_threshold(messages, signal):
    """保持 Token 数在 3000 以内"""
    MAX_TOKENS = 3000
    
    while count_messages_tokens(messages) > MAX_TOKENS:
        if len(messages) <= 2:
            break
        # 删除最旧的消息（保留 system 和最新）
        messages.pop(0)
    
    return messages
```

**策略 3：智能摘要（高级）**

```python
async def smart_summary(messages, signal):
    """
    保留最近 5 条，旧消息用摘要替代
    （需要额外的 LLM 调用来生成摘要）
    """
    if len(messages) <= 5:
        return messages
    
    # 保留最近 5 条
    recent = messages[-5:]
    
    # 旧消息生成摘要（简化示例）
    old_messages = messages[:-5]
    summary_text = f"[之前对话摘要: 共 {len(old_messages)} 条消息]"
    
    from ai.types import AssistantMessage, TextContent
    summary_msg = AssistantMessage(content=[TextContent(text=summary_text)])
    
    return [summary_msg] + recent
```

---

## 4. 状态保存与恢复

### 4.1 保存对话状态

```python
import json
from datetime import datetime

def save_conversation(agent, filepath: str, metadata: dict = None):
    """
    保存对话到 JSON 文件
    
    Args:
        agent: Agent 实例
        filepath: 保存路径
        metadata: 额外元数据（如标题、标签）
    """
    state = agent.state
    
    data = {
        "version": "1.0",
        "saved_at": datetime.now().isoformat(),
        "metadata": metadata or {},
        "conversation": {
            "system_prompt": state.system_prompt,
            "thinking_level": state.thinking_level,
            "message_count": len(state.messages),
            "messages": []
        }
    }
    
    # 序列化消息
    for msg in state.messages:
        msg_data = {
            "role": msg.role,
            "timestamp": getattr(msg, "timestamp", None),
            "content": []
        }
        
        for content in msg.content:
            content_data = {"type": content.type}
            
            if content.type == "text":
                content_data["text"] = content.text
            elif content.type == "image":
                content_data["mime_type"] = content.mime_type
                content_data["data"] = content.data[:100] + "..."  # 截断
            elif content.type == "toolCall":
                content_data["name"] = content.name
                content_data["arguments"] = content.arguments
            
            msg_data["content"].append(content_data)
        
        data["conversation"]["messages"].append(msg_data)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"对话已保存: {filepath}")
```

### 4.2 恢复对话状态

```python
def load_conversation(filepath: str, stream_fn) -> Agent:
    """
    从 JSON 文件恢复对话
    
    Args:
        filepath: 文件路径
        stream_fn: 流式函数（需要重新提供）
    
    Returns:
        恢复好的 Agent 实例
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    conv_data = data["conversation"]
    
    # 重建消息列表
    from ai.types import UserMessage, AssistantMessage, TextContent
    
    messages = []
    for msg_data in conv_data["messages"]:
        # 重建 content
        content_list = []
        for c in msg_data["content"]:
            if c["type"] == "text":
                content_list.append(TextContent(text=c["text"]))
            # 其他类型可以扩展...
        
        # 创建消息对象
        if msg_data["role"] == "user":
            messages.append(UserMessage(content=content_list))
        else:
            messages.append(AssistantMessage(content=content_list))
    
    # 重建 State
    from agent.types import AgentState
    state = AgentState(
        system_prompt=conv_data["system_prompt"],
        thinking_level=conv_data["thinking_level"],
        messages=messages
    )
    
    # 创建 Agent
    from ai.providers import KimiProvider
    provider = KimiProvider()
    
    agent = Agent(AgentOptions(
        stream_fn=stream_fn,
        initial_state=state
    ))
    agent.set_model(provider.get_model())
    
    print(f"对话已恢复: {len(messages)} 条消息")
    return agent
```

### 4.3 使用示例

```python
# 第 1 次对话
agent = create_agent()
await agent.prompt("你好，我叫小明")
await agent.wait_for_idle()

# 保存
save_conversation(agent, "chat_2024_01_15.json", 
                  metadata={"topic": "自我介绍", "user": "xiaoming"})

# ... 几天后再打开

# 恢复
async def stream_fn(model, context, options):
    provider = KimiProvider()
    return provider.stream_simple(model, context, options)

agent = load_conversation("chat_2024_01_15.json", stream_fn)

# 继续对话 - Agent 还记得"小明"
await agent.prompt("我叫什么名字？")
await agent.wait_for_idle()
# 输出："你叫小明"
```

---

## 5. 实战练习

### 练习 1：实现对话轮数限制

当对话超过 10 轮时，自动提醒用户并建议新建对话。

<details>
<summary>参考答案</summary>

```python
def create_turn_limit_callback(max_turns=10):
    """创建轮数限制回调"""
    warned = False
    
    def on_event(event):
        nonlocal warned
        
        if event.get("type") == "agent_end":
            # 计算轮数（user + assistant = 1 轮）
            turn_count = len(agent.state.messages) // 2
            
            if turn_count >= max_turns and not warned:
                print(f"\n⚠️  提醒：对话已有 {turn_count} 轮")
                print("💡 建议：新建对话可以获得更好的性能")
                warned = True
    
    return on_event

agent.subscribe(create_turn_limit_callback(10))
```

</details>

### 练习 2：实现自动保存

每 3 轮对话自动保存到文件。

<details>
<summary>参考答案</summary>

```python
def create_auto_save_callback(save_dir="./saves"):
    """创建自动保存回调"""
    from pathlib import Path
    import os
    
    Path(save_dir).mkdir(exist_ok=True)
    last_saved_turn = 0
    
    def on_event(event):
        nonlocal last_saved_turn
        
        if event.get("type") == "agent_end":
            turn_count = len(agent.state.messages) // 2
            
            # 每 3 轮保存一次
            if turn_count - last_saved_turn >= 3:
                filepath = f"{save_dir}/auto_save_{datetime.now():%Y%m%d_%H%M%S}.json"
                save_conversation(agent, filepath)
                print(f"💾 自动保存: {filepath}")
                last_saved_turn = turn_count
    
    return on_event
```

</details>

### 练习 3：上下文可视化

实现一个函数，打印当前上下文的 Token 分布。

<details>
<summary>参考答案</summary>

```python
def visualize_context(agent):
    """可视化上下文"""
    messages = agent.state.messages
    total_tokens = 0
    
    print("=== 上下文分析 ===")
    print(f"总消息数: {len(messages)}")
    print()
    
    for i, msg in enumerate(messages):
        role = "用户" if msg.role == "user" else "助手"
        text = msg.content[0].text if msg.content else ""
        tokens = estimate_tokens(text)
        total_tokens += tokens
        
        # 显示进度条
        bar = "█" * min(tokens // 50, 20)
        
        print(f"{i+1:2d}. {role:4s} [{bar:<20s}] {tokens:4d} tokens")
        print(f"    {text[:60]}...")
        print()
    
    print(f"总计: {total_tokens} tokens")
    print(f"估算成本: ${total_tokens * 0.00001:.4f}")
```

</details>

---

## 6. 常见问题

**Q1: 为什么 Agent 能"记得"之前的对话？**

Agent 本身不记忆，只是把历史消息发给 LLM。LLM 根据完整历史生成回复。

类比：
```
Agent = 传话员
LLM = 有无限笔记本的智者

每次对话，传话员把完整笔记本给智者
智者基于全部记录回答
```

**Q2: 对话历史会无限增长吗？**

默认会。需要通过 `transform_context` 实现修剪策略。

**Q3: 如何清除特定轮次的记忆？**

```python
# 删除前 2 条消息（第 1 轮）
agent.state.messages = agent.state.messages[2:]

# 或替换为摘要
old_messages = agent.state.messages[:-2]
summary = create_summary(old_messages)
agent.state.messages = [summary] + agent.state.messages[-2:]
```

**Q4: 保存状态后，模型信息会丢失吗？**

会！`AgentState` 不包含模型信息，恢复后需要重新设置：

```python
agent = Agent(AgentOptions(initial_state=loaded_state))
agent.set_model(provider.get_model())  # 重新设置模型
```

---

## 7. 下一步

完成本文档后，你应该能：
- ✅ 理解多轮对话的工作原理
- ✅ 实现上下文修剪策略
- ✅ 保存和恢复对话状态
- ✅ 优化长对话的性能

**下一步：** [文档 4：高级功能](04_advanced_features.md)

---

## 附录：上下文管理速查表

| 场景 | 解决方案 |
|------|---------|
| 对话过长 | `transform_context` 修剪 |
| 保存对话 | 序列化 `agent.state` |
| 恢复对话 | `AgentOptions(initial_state=...)` |
| 清除历史 | `agent.clear_messages()` 或 `reset()` |
| 查看长度 | `len(agent.state.messages)` |
| Token 估算 | 按字符数 × 1.5 估算 |
