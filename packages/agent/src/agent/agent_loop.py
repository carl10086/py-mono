"""
Agent Loop - 核心循环逻辑

Agent Loop 是 Agent 的核心执行引擎，负责：
1. 协调 LLM 调用和流式响应处理
2. 管理消息生命周期和事件发射
3. 支持 steering 和 follow-up 消息队列
4. 提供工具调用执行框架（通过 config）

架构位置：
    Agent.prompt()
        ↓
    run_agent_loop() / run_agent_loop_continue()
        ↓
    _run_loop() → _stream_assistant_response()
        ↓
    stream_fn() (调用 LLM)
        ↓
    事件流 → emit() → Agent._process_loop_event()

执行流程：
    1. 构建上下文（system_prompt + messages + tools）
    2. 调用 LLM 获取流式响应
    3. 解析流事件（start, text_delta, done 等）
    4. 发射 Agent 事件给订阅者
    5. 更新消息历史

线程安全：
    - 无共享状态，每个调用独立
    - 通过 signal 参数支持取消
    - 事件回调是同步的

示例：
    >>> from agent.agent_loop import run_agent_loop
    >>> from agent.types import AgentContext, AgentLoopConfig
    >>>
    >>> context = AgentContext(
    ...     system_prompt="你是一个助手",
    ...     messages=[],
    ...     tools=[]
    ... )
    >>> config = AgentLoopConfig(model=model, convert_to_llm=convert_fn)
    >>>
    >>> def on_event(event):
    ...     print(f"事件: {event.get('type')}")
    >>>
    >>> await run_agent_loop(
    ...     prompts=[UserMessage(text="你好")],
    ...     context=context,
    ...     config=config,
    ...     emit=on_event,
    ...     stream_fn=stream_fn
    ... )
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Awaitable

from ai.types import AssistantMessage, Context, SimpleStreamOptions, ToolResultMessage

from agent.types import AgentContext, AgentEvent, AgentLoopConfig, AgentMessage

AgentEventSink = Callable[[AgentEvent], Awaitable[None] | None]
"""事件接收函数类型

接收 Agent 事件并处理。可以是同步或异步函数。

参数：
    event: 事件字典，包含 type 字段

示例：
    >>> async def on_event(event):
    ...     if event.get("type") == "message_end":
    ...         await save_to_db(event.get("message"))
"""


async def run_agent_loop(
    prompts: list[AgentMessage],
    context: AgentContext,
    config: AgentLoopConfig,
    emit: AgentEventSink,
    signal: Any = None,
    stream_fn: Any = None,
) -> list[AgentMessage]:
    """启动新的 Agent Loop

    开始一个新的对话循环，处理用户提示并获取助手回复。
    这是 Agent 的主要入口点。

    参数：
        prompts: 初始提示消息列表
            这些消息会被添加到上下文并触发 LLM 调用
        context: Agent 上下文
            包含 system_prompt、历史消息和工具列表
        config: Loop 配置
            包含模型、转换函数、钩子等配置
        emit: 事件接收函数
            接收 Agent 生命周期事件
        signal: 取消信号（可选）
            用于取消正在执行的 Loop
        stream_fn: 流式调用函数
            调用 LLM 的函数，返回事件流

    返回：
        新产生的消息列表（助手回复 + 工具结果）

    异常：
        ValueError: 如果 stream_fn 为 None
        其他异常会编码在返回的流中

    事件序列：
        1. agent_start
        2. turn_start
        3. message_start (prompt)
        4. message_end (prompt)
        5. message_start (assistant)
        6. message_update × N (流式)
        7. message_end (assistant)
        8. turn_end
        9. agent_end

    示例：
        >>> new_messages = await run_agent_loop(
        ...     prompts=[UserMessage(text="你好")],
        ...     context=context,
        ...     config=config,
        ...     emit=lambda e: print(e.get("type")),
        ...     stream_fn=provider.stream_simple
        ... )
        >>> print(f"新增 {len(new_messages)} 条消息")
    """
    new_messages: list[AgentMessage] = list(prompts)
    current_context = AgentContext(
        system_prompt=context.system_prompt,
        messages=list(context.messages) + list(prompts),
        tools=context.tools,
    )

    await _emit(emit, {"type": "agent_start"})
    await _emit(emit, {"type": "turn_start"})

    for prompt in prompts:
        await _emit(emit, {"type": "message_start", "message": prompt})
        await _emit(emit, {"type": "message_end", "message": prompt})

    await _run_loop(current_context, new_messages, config, signal, emit, stream_fn)
    return new_messages


async def run_agent_loop_continue(
    context: AgentContext,
    config: AgentLoopConfig,
    emit: AgentEventSink,
    signal: Any = None,
    stream_fn: Any = None,
) -> list[AgentMessage]:
    """从当前上下文继续 Agent Loop

    在不添加新消息的情况下继续对话。
    用于重试、处理 steering 消息等场景。

    参数：
        context: Agent 上下文（最后消息必须是 user 或 toolResult）
        config: Loop 配置
        emit: 事件接收函数
        signal: 取消信号（可选）
        stream_fn: 流式调用函数

    返回：
        新产生的消息列表

    异常：
        ValueError: 如果上下文为空
        ValueError: 如果最后消息是 assistant

    使用场景：
        1. 重试失败的请求
        2. 处理 steering 消息后继续
        3. 工具调用后的自动继续

    示例：
        >>> # 重试机制
        >>> try:
        ...     await run_agent_loop_continue(context, config, emit, stream_fn)
        ... except Exception as e:
        ...     if retry_count < 3:
        ...         await run_agent_loop_continue(context, config, emit, stream_fn)
    """
    if not context.messages:
        raise ValueError("Cannot continue: no messages in context")

    last_message = context.messages[-1]
    if getattr(last_message, "role", "") == "assistant":
        raise ValueError("Cannot continue from message role: assistant")

    new_messages: list[AgentMessage] = []
    current_context = AgentContext(
        system_prompt=context.system_prompt,
        messages=list(context.messages),
        tools=context.tools,
    )

    await _emit(emit, {"type": "agent_start"})
    await _emit(emit, {"type": "turn_start"})

    await _run_loop(current_context, new_messages, config, signal, emit, stream_fn)
    return new_messages


async def _emit(emit: AgentEventSink, event: AgentEvent) -> None:
    """发送事件

    内部函数，处理同步/异步 emit 函数。

    参数：
        emit: 事件接收函数
        event: 事件字典
    """
    result = emit(event)
    if result is not None:
        await result


async def _run_loop(
    current_context: AgentContext,
    new_messages: list[AgentMessage],
    config: AgentLoopConfig,
    signal: Any,
    emit: AgentEventSink,
    stream_fn: Any,
) -> None:
    """主循环逻辑

    核心执行逻辑，处理单个 Turn：
    1. 获取 steering 消息
    2. 调用 LLM
    3. 发射事件
    4. 处理 follow-up

    参数：
        current_context: 当前上下文（会被修改）
        new_messages: 新消息列表（会被追加）
        config: Loop 配置
        signal: 取消信号
        emit: 事件接收函数
        stream_fn: 流式调用函数

    注意：
        - current_context 和 new_messages 会被修改
        - 在异常时发射 agent_end 事件
    """
    if stream_fn is None:
        raise ValueError("stream_fn is required")

    # 获取助手响应
    message = await _stream_assistant_response(current_context, config, signal, emit, stream_fn)
    new_messages.append(message)

    await _emit(emit, {"type": "turn_end", "message": message, "toolResults": []})
    await _emit(emit, {"type": "agent_end", "messages": new_messages})


async def _stream_assistant_response(
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Any,
    emit: AgentEventSink,
    stream_fn: Any,
) -> AssistantMessage:
    """流式获取助手响应

    调用 LLM 并处理流式响应，发射相应事件。

    参数：
        context: Agent 上下文（会被修改，添加助手消息）
        config: Loop 配置
        signal: 取消信号
        emit: 事件接收函数
        stream_fn: 流式调用函数

    返回：
        完整的助手消息

    流事件处理：
        - start: 开始生成，获取 partial message
        - text_delta/thinking_delta: 内容更新，发射 message_update
        - done: 生成完成，返回最终消息

    消息构建逻辑：
        1. 收到 start 事件：创建 partial message，发射 message_start
        2. 收到 delta 事件：更新 partial message，发射 message_update
        3. 收到 done 事件：获取最终消息，发射 message_end

    示例：
        >>> message = await _stream_assistant_response(
        ...     context, config, signal, emit, stream_fn
        ... )
        >>> print(f"助手回复: {message.content[0].text}")
    """
    print()

    # 转换为 LLM 消息
    if config.convert_to_llm:
        llm_messages = await config.convert_to_llm(list(context.messages))
    else:
        llm_messages = list(context.messages)

    # 构建 LLM 上下文
    llm_context = Context(
        system_prompt=context.system_prompt,
        messages=llm_messages,
        tools=list(context.tools) if context.tools else [],
    )

    # 获取 API Key
    api_key: str | None = None
    if config.get_api_key and config.model:
        api_key = await config.get_api_key(config.model.provider)

    # 调用 LLM
    options = SimpleStreamOptions(api_key=api_key, signal=signal)
    stream = await stream_fn(config.model, llm_context, options)

    partial_message: AssistantMessage | None = None
    added_partial = False

    async for event in stream:
        event_type = getattr(event, "type", "")

        if event_type == "start":
            partial_message = getattr(event, "partial", None)
            if partial_message:
                context.messages.append(partial_message)
                added_partial = True
                await _emit(emit, {"type": "message_start", "message": partial_message})

        elif event_type in ("text_delta", "thinking_delta"):
            if partial_message:
                partial_message = getattr(event, "partial", partial_message)
                context.messages[-1] = partial_message
                await _emit(
                    emit,
                    {
                        "type": "message_update",
                        "message": partial_message,
                        "assistantMessageEvent": event,
                    },
                )

        elif event_type == "done":
            final_message = await stream.result()
            if added_partial:
                context.messages[-1] = final_message
            else:
                context.messages.append(final_message)

            if not added_partial:
                await _emit(emit, {"type": "message_start", "message": final_message})

            await _emit(emit, {"type": "message_end", "message": final_message})
            return final_message

    # 兜底：获取最终结果
    final_message = await stream.result()
    if added_partial:
        context.messages[-1] = final_message
    else:
        context.messages.append(final_message)
        await _emit(emit, {"type": "message_start", "message": final_message})

    await _emit(emit, {"type": "message_end", "message": final_message})
    return final_message
