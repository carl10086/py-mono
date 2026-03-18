"""
Agent Loop - 核心循环逻辑（对齐 pi-mono 架构）

Agent Loop 是 Agent 的核心执行引擎，负责：
1. 协调 LLM 调用和流式响应处理
2. 管理消息生命周期和事件发射
3. 支持 steering 和 follow-up 消息队列
4. 提供工具调用执行框架

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

双循环结构（对齐 pi-mono）：
    外循环：处理 follow-up 消息
        while True:
            内循环：处理 tool calls + steering
                while has_tool_calls or pending_messages:
                    # 注入 steering 消息
                    # 调用 LLM
                    # 执行 tool calls
                    # 检查 steering
            # 检查 follow-up
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ai.types import (
    AssistantMessage,
    Context,
    SimpleStreamOptions,
    TextContent,
    ToolCall,
    ToolResultMessage,
)

from agent.types import (
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentStartEvent,
    AgentEndEvent,
    TurnStartEvent,
    TurnEndEvent,
    MessageStartEvent,
    MessageEndEvent,
    AgentTool,
    AgentToolResult,
    BeforeToolCallContext,
    AfterToolCallContext,
    BeforeToolCallResult,
    AfterToolCallResult,
)

AgentEventSink = Callable[[AgentEvent], Awaitable[None] | None]


async def run_agent_loop(
    prompts: list[AgentMessage],
    context: AgentContext,
    config: AgentLoopConfig,
    emit: AgentEventSink,
    signal: Any = None,
    stream_fn: Any = None,
) -> list[AgentMessage]:
    """启动新的 Agent Loop

    参数：
        prompts: 初始提示消息列表
        context: Agent 上下文
        config: Loop 配置
        emit: 事件接收函数
        signal: 取消信号
        stream_fn: 流式调用函数

    返回：
        新产生的消息列表
    """
    new_messages: list[AgentMessage] = list(prompts)
    current_context = AgentContext(
        system_prompt=context.system_prompt,
        messages=list(context.messages) + list(prompts),
        tools=context.tools,
    )

    await _emit(emit, AgentStartEvent(type="agent_start"))
    await _emit(emit, TurnStartEvent(type="turn_start"))

    for prompt in prompts:
        await _emit(emit, MessageStartEvent(type="message_start", message=prompt))
        await _emit(emit, MessageEndEvent(type="message_end", message=prompt))

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

    参数：
        context: Agent 上下文（最后消息必须是 user 或 toolResult）
        config: Loop 配置
        emit: 事件接收函数
        signal: 取消信号
        stream_fn: 流式调用函数

    返回：
        新产生的消息列表
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

    await _emit(emit, AgentStartEvent(type="agent_start"))
    await _emit(emit, TurnStartEvent(type="turn_start"))

    await _run_loop(current_context, new_messages, config, signal, emit, stream_fn)
    return new_messages


async def _emit(emit: AgentEventSink, event: AgentEvent) -> None:
    """发送事件"""
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
    """主循环逻辑（双循环结构）

    外循环：处理 follow-up 消息
    内循环：处理 tool calls 和 steering 消息
    """
    if stream_fn is None:
        raise ValueError("stream_fn is required")

    first_turn = True
    # 初始检查 steering 消息
    pending_messages: list[AgentMessage] = await _get_steering_messages(config) or []

    # 外循环：当 follow-up 消息到达时继续
    while True:
        has_more_tool_calls = True

        # 内循环：处理 tool calls 和 steering 消息
        while has_more_tool_calls or pending_messages:
            if not first_turn:
                await _emit(emit, TurnStartEvent(type="turn_start"))
            else:
                first_turn = False

            # 处理 pending 消息（注入 steering 消息）
            if pending_messages:
                for message in pending_messages:
                    await _emit(emit, MessageStartEvent(type="message_start", message=message))
                    await _emit(emit, MessageEndEvent(type="message_end", message=message))
                    current_context.messages.append(message)
                    new_messages.append(message)
                pending_messages = []

            # 流式获取助手响应
            message = await _stream_assistant_response(
                current_context, config, signal, emit, stream_fn
            )
            new_messages.append(message)

            # 检查是否出错或中止
            if message.stop_reason in ("error", "aborted"):
                await _emit(emit, TurnEndEvent(type="turn_end", message=message, tool_results=[]))
                await _emit(emit, AgentEndEvent(type="agent_end", messages=new_messages))
                return

            # 检查是否有 tool calls
            tool_calls = [c for c in message.content if getattr(c, "type", "") == "toolCall"]
            has_more_tool_calls = len(tool_calls) > 0

            tool_results: list[ToolResultMessage] = []
            if has_more_tool_calls:
                # 执行 tool calls
                tool_results = await _execute_tool_calls(
                    current_context, message, config, signal, emit
                )
                # 添加 tool results 到上下文
                for result in tool_results:
                    current_context.messages.append(result)
                    new_messages.append(result)

            await _emit(
                emit, TurnEndEvent(type="turn_end", message=message, tool_results=tool_results)
            )

            # 检查新的 steering 消息
            pending_messages = await _get_steering_messages(config) or []

        # 内循环结束：没有 tool calls 和 steering 消息了
        # 检查 follow-up 消息
        follow_up_messages = await _get_follow_up_messages(config) or []
        if follow_up_messages:
            # 设置 pending 让内循环处理 follow-up
            pending_messages = follow_up_messages
            continue

        # 没有更多消息，退出外循环
        break

    await _emit(emit, AgentEndEvent(type="agent_end", messages=new_messages))


async def _get_steering_messages(config: AgentLoopConfig) -> list[AgentMessage] | None:
    """获取 steering 消息"""
    if config.get_steering_messages:
        return await config.get_steering_messages()
    return None


async def _get_follow_up_messages(config: AgentLoopConfig) -> list[AgentMessage] | None:
    """获取 follow-up 消息"""
    if config.get_follow_up_messages:
        return await config.get_follow_up_messages()
    return None


async def _stream_assistant_response(
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Any,
    emit: AgentEventSink,
    stream_fn: Any,
) -> AssistantMessage:
    """流式获取助手响应"""
    print()

    # 应用上下文转换
    messages = context.messages
    if config.transform_context:
        messages = await config.transform_context(messages, signal)

    # 转换为 LLM 消息
    if config.convert_to_llm:
        llm_messages = await config.convert_to_llm(messages)
    else:
        llm_messages = list(messages)

    # 构建 LLM 上下文
    # 将 AgentTool 转换为 ai.types.Tool
    from ai.types import Tool

    llm_tools = None
    if context.tools:
        llm_tools = [
            Tool(name=t.name, description=t.description, parameters=t.parameters)
            for t in context.tools
        ]

    llm_context = Context(
        system_prompt=context.system_prompt,
        messages=llm_messages,
        tools=llm_tools,
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
                await _emit(emit, MessageStartEvent(type="message_start", message=partial_message))

        elif event_type in ("text_delta", "thinking_delta"):
            if partial_message:
                partial_message = getattr(event, "partial", partial_message)
                context.messages[-1] = partial_message
                await _emit(
                    emit,
                    {
                        "type": "message_update",
                        "message": partial_message,
                        "assistant_message_event": event,
                    },
                )

        elif event_type == "done":
            final_message = await stream.result()
            if added_partial:
                context.messages[-1] = final_message
            else:
                context.messages.append(final_message)

            if not added_partial:
                await _emit(emit, MessageStartEvent(type="message_start", message=final_message))

            await _emit(emit, MessageEndEvent(type="message_end", message=final_message))
            return final_message

    # 兜底：获取最终结果
    final_message = await stream.result()
    if added_partial:
        context.messages[-1] = final_message
    else:
        context.messages.append(final_message)
        await _emit(emit, MessageStartEvent(type="message_start", message=final_message))

    await _emit(emit, MessageEndEvent(type="message_end", message=final_message))
    return final_message


async def _execute_tool_calls(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    config: AgentLoopConfig,
    signal: Any,
    emit: AgentEventSink,
) -> list[ToolResultMessage]:
    """执行工具调用

    根据配置选择顺序或并行执行模式
    """
    tool_calls = [c for c in assistant_message.content if getattr(c, "type", "") == "toolCall"]

    if config.tool_execution == "sequential":
        return await _execute_tool_calls_sequential(
            current_context, assistant_message, tool_calls, config, signal, emit
        )
    return await _execute_tool_calls_parallel(
        current_context, assistant_message, tool_calls, config, signal, emit
    )


async def _execute_tool_calls_sequential(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_calls: list[Any],
    config: AgentLoopConfig,
    signal: Any,
    emit: AgentEventSink,
) -> list[ToolResultMessage]:
    """顺序执行工具调用"""
    results: list[ToolResultMessage] = []

    for tool_call in tool_calls:
        tool_call_id = getattr(tool_call, "id", "")
        tool_name = getattr(tool_call, "name", "")
        tool_args = getattr(tool_call, "arguments", {})

        await _emit(
            emit,
            {
                "type": "tool_execution_start",
                "toolCallId": tool_call_id,
                "toolName": tool_name,
                "args": tool_args,
            },
        )

        result = await _execute_single_tool_call(
            current_context, assistant_message, tool_call, config, signal, emit
        )
        results.append(result)

    return results


async def _execute_tool_calls_parallel(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_calls: list[Any],
    config: AgentLoopConfig,
    signal: Any,
    emit: AgentEventSink,
) -> list[ToolResultMessage]:
    """并行执行工具调用"""
    results: list[ToolResultMessage] = []
    pending_tasks: list[tuple[Any, Any]] = []

    for tool_call in tool_calls:
        tool_call_id = getattr(tool_call, "id", "")
        tool_name = getattr(tool_call, "name", "")
        tool_args = getattr(tool_call, "arguments", {})

        await _emit(
            emit,
            {
                "type": "tool_execution_start",
                "toolCallId": tool_call_id,
                "toolName": tool_name,
                "args": tool_args,
            },
        )

        # 准备工具调用
        prepared = await _prepare_tool_call(
            current_context, assistant_message, tool_call, config, signal
        )
        pending_tasks.append((tool_call, prepared))

    # 并行执行
    executions: list[tuple[Any, Any]] = []
    for tool_call, prepared in pending_tasks:
        if isinstance(prepared, dict) and prepared.get("kind") == "immediate":
            # 立即结果（如 before_hook 拦截）
            result = prepared["result"]
            is_error = prepared.get("is_error", False)
            executions.append((tool_call, (result, is_error)))
        else:
            # 需要异步执行
            execution = _execute_prepared_tool_call(prepared, signal, emit)
            executions.append((tool_call, execution))

    # 收集结果
    for tool_call, execution in executions:
        if isinstance(execution, tuple):
            result, is_error = execution
        else:
            result, is_error = await execution

        final_result = await _finalize_tool_call_result(
            current_context, assistant_message, tool_call, result, is_error, config, signal, emit
        )
        results.append(final_result)

    return results


async def _execute_single_tool_call(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_call: Any,
    config: AgentLoopConfig,
    signal: Any,
    emit: AgentEventSink,
) -> ToolResultMessage:
    """执行单个工具调用"""
    tool_call_id = getattr(tool_call, "id", "")
    tool_name = getattr(tool_call, "name", "")

    # 准备工具调用
    prepared = await _prepare_tool_call(
        current_context, assistant_message, tool_call, config, signal
    )

    if isinstance(prepared, dict) and prepared.get("kind") == "immediate":
        # 立即结果（如 before_hook 拦截）
        result = prepared["result"]
        is_error = prepared.get("is_error", False)
    else:
        # 执行工具
        result, is_error = await _execute_prepared_tool_call(prepared, signal, emit)

    # 最终化结果
    return await _finalize_tool_call_result(
        current_context, assistant_message, tool_call, result, is_error, config, signal, emit
    )


async def _prepare_tool_call(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_call: Any,
    config: AgentLoopConfig,
    signal: Any,
) -> Any:
    """准备工具调用

    查找工具、验证参数、执行 before_hook
    返回 prepared 对象或立即结果（如果被拦截）
    """
    tool_call_id = getattr(tool_call, "id", "")
    tool_name = getattr(tool_call, "name", "")
    tool_args = getattr(tool_call, "arguments", {})

    # 查找工具
    tool = None
    if current_context.tools:
        for t in current_context.tools:
            if getattr(t, "name", "") == tool_name:
                tool = t
                break

    if not tool:
        return {
            "kind": "immediate",
            "result": _create_error_tool_result(f"Tool {tool_name} not found"),
            "is_error": True,
        }

    try:
        # 执行 before_tool_call hook
        if config.before_tool_call:
            ctx = BeforeToolCallContext(
                assistant_message=assistant_message,
                tool_call=ToolCall(id=tool_call_id, name=tool_name, arguments=tool_args),
                args=tool_args,
                context=current_context,
            )
            before_result = await config.before_tool_call(ctx, signal)
            if before_result and before_result.block:
                reason = before_result.reason or "Tool execution was blocked"
                return {
                    "kind": "immediate",
                    "result": _create_error_tool_result(reason),
                    "is_error": True,
                }

        return {
            "kind": "prepared",
            "tool_call": tool_call,
            "tool": tool,
            "args": tool_args,
        }
    except Exception as e:
        return {
            "kind": "immediate",
            "result": _create_error_tool_result(str(e)),
            "is_error": True,
        }


async def _execute_prepared_tool_call(
    prepared: Any,
    signal: Any,
    emit: AgentEventSink,
) -> tuple[AgentToolResult[Any], bool]:
    """执行准备好的工具调用"""
    tool = prepared.get("tool")
    tool_call_id = getattr(prepared.get("tool_call"), "id", "")
    tool_name = getattr(prepared.get("tool_call"), "name", "")
    args = prepared.get("args", {})

    update_events: list[Any] = []

    def on_update(partial_result: AgentToolResult[Any]) -> None:
        update_events.append(
            {
                "type": "tool_execution_update",
                "toolCallId": tool_call_id,
                "toolName": tool_name,
                "args": args,
                "partialResult": partial_result,
            }
        )

    try:
        result = await tool.execute(tool_call_id, args, signal, on_update)

        # 发送所有更新事件
        for event in update_events:
            await _emit(emit, event)

        return result, False
    except Exception as e:
        # 发送所有更新事件
        for event in update_events:
            await _emit(emit, event)

        return _create_error_tool_result(str(e)), True


async def _finalize_tool_call_result(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_call: Any,
    result: AgentToolResult[Any],
    is_error: bool,
    config: AgentLoopConfig,
    signal: Any,
    emit: AgentEventSink,
) -> ToolResultMessage:
    """最终化工具调用结果

    执行 after_tool_call hook 并创建 ToolResultMessage
    """
    tool_call_id = getattr(tool_call, "id", "")
    tool_name = getattr(tool_call, "name", "")
    args = getattr(tool_call, "arguments", {})

    # 执行 after_tool_call hook
    if config.after_tool_call:
        ctx = AfterToolCallContext(
            assistant_message=assistant_message,
            tool_call=ToolCall(id=tool_call_id, name=tool_name, arguments=args),
            args=args,
            result=result,
            is_error=is_error,
            context=current_context,
        )
        after_result = await config.after_tool_call(ctx, signal)
        if after_result:
            if after_result.content is not None:
                result.content = after_result.content
            if after_result.details is not None:
                result.details = after_result.details
            if after_result.is_error is not None:
                is_error = after_result.is_error

    # 发射 tool_execution_end 事件
    await _emit(
        emit,
        {
            "type": "tool_execution_end",
            "toolCallId": tool_call_id,
            "toolName": tool_name,
            "result": result,
            "isError": is_error,
        },
    )

    # 创建 ToolResultMessage
    import time

    tool_result_message = ToolResultMessage(
        role="toolResult",
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        content=list(result.content),
        details=result.details,
        is_error=is_error,
        timestamp=int(time.time() * 1000),
    )

    await _emit(emit, MessageStartEvent(type="message_start", message=tool_result_message))
    await _emit(emit, MessageEndEvent(type="message_end", message=tool_result_message))

    return tool_result_message


def _create_error_tool_result(message: str) -> AgentToolResult[Any]:
    """创建错误工具结果"""
    return AgentToolResult(
        content=[TextContent(text=message)],
        details={},
    )
