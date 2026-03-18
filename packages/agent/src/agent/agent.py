"""
Agent 类 - Agent 运行时管理

提供高层 Agent 接口，管理状态、事件订阅、消息队列等。
对标 pi-mono TypeScript 实现。

架构位置：
    用户代码
        ↓
    Agent 类（本文件）
        ↓
    Agent Loop（agent_loop.py）
        ↓
    AI Stream（py-mono-ai）
        ↓
    LLM Provider

核心职责：
1. 状态管理：维护对话历史、系统提示、工具列表
2. 事件系统：订阅/发布机制，支持 UI 更新和日志记录
3. 消息队列：steering 和 follow-up 消息管理
4. 生命周期：prompt → loop → stream → event → state

使用示例：
    >>> from agent import Agent, AgentOptions
    >>> from ai.providers import KimiProvider
    >>>
    >>> # 创建 Agent
    >>> provider = KimiProvider()
    >>> async def stream_fn(model, context, options):
    ...     return provider.stream_simple(model, context, options)
    >>>
    >>> agent = Agent(AgentOptions(stream_fn=stream_fn))
    >>> agent.set_model(provider.get_model())
    >>> agent.set_system_prompt("你是一个有帮助的助手")
    >>>
    >>> # 订阅事件
    >>> agent.subscribe(lambda e: print(f"事件: {e.get('type')}"))
    >>>
    >>> # 发送消息
    >>> await agent.prompt("你好！")
    >>> await agent.wait_for_idle()
"""

from __future__ import annotations

import asyncio
from typing import Any, cast

from ai.types import (
    AssistantMessage,
    ImageContent,
    Model,
    TextContent,
    ThinkingBudgets,
    Transport,
)

from agent.agent_loop import run_agent_loop, run_agent_loop_continue
from agent.types import (
    AfterToolCallHook,
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentState,
    AgentTool,
    BeforeToolCallHook,
    StreamFn,
    ThinkingLevel,
    ToolExecutionMode,
)

# ============================================================================
# AgentOptions
# ============================================================================


class AgentOptions:
    """Agent 配置选项

    用于配置 Agent 的行为和扩展点。

    所有选项都是可选的，使用默认值即可快速开始。
    高级用法可以通过自定义函数实现特定需求。

    配置分类：
    1. 初始状态：initial_state
    2. 消息处理：convert_to_llm, transform_context
    3. 队列模式：steering_mode, follow_up_mode
    4. 流式调用：stream_fn, transport
    5. 认证：get_api_key
    6. 思考模式：thinking_budgets
    7. 工具钩子：before_tool_call, after_tool_call

    示例：
        >>> # 基础配置
        >>> opts = AgentOptions()
        >>> agent = Agent(opts)

        >>> # 高级配置
        >>> opts = AgentOptions(
        ...     stream_fn=custom_stream,
        ...     steering_mode="one-at-a-time",
        ...     tool_execution="parallel",
        ...     before_tool_call=permission_check_hook
        ... )
    """

    initial_state: AgentState | None
    """初始状态

    用于恢复之前的会话。保存 agent.state 后可以恢复：

    >>> saved_state = agent.state
    >>> # ... 稍后恢复
    >>> agent = Agent(AgentOptions(initial_state=saved_state))
    """

    convert_to_llm: Callable[[list[AgentMessage]], Awaitable[list[Any]]] | None
    """消息转换函数

    将 AgentMessage[] 转换为 LLM 兼容的 Message[]。

    默认行为：
        过滤 role 为 user/assistant/toolResult 的消息

    自定义场景：
        - 上下文压缩：截断过长的历史
        - 格式转换：特殊消息类型处理
    """

    transform_context: Callable[[list[AgentMessage], Any], Awaitable[list[AgentMessage]]] | None
    """上下文转换函数

    在 convert_to_llm 之前应用，用于上下文修剪等。

    执行顺序：messages → transform_context → convert_to_llm → LLM
    """

    steering_mode: Literal["all", "one-at-a-time"]
    """Steering 模式

    - "all": 一次发送所有 steering 消息
    - "one-at-a-time": 每次只发送一条（默认）
    """

    follow_up_mode: Literal["all", "one-at-a-time"]
    """Follow-up 模式

    - "all": 一次发送所有 follow-up 消息
    - "one-at-a-time": 每次只发送一条（默认）
    """

    stream_fn: StreamFn | None
    """自定义流式函数

    用于自定义 LLM 调用逻辑，如代理后端、自定义路由等。

    默认使用 provider.stream_simple
    """

    session_id: str | None
    """会话标识符

    用于支持会话级缓存的 provider（如 OpenAI Codex）
    """

    get_api_key: Callable[[str], Awaitable[str | None] | str | None] | None
    """API Key 动态获取函数

    参数：provider 名称
    返回：API Key 或 None

    用于动态令牌（如 OAuth）
    """

    on_payload: Any | None
    """Payload 检查函数

    在发送给 provider 前检查或修改请求 payload
    """

    thinking_budgets: ThinkingBudgets | None
    """思考预算配置

    自定义各级思考等级的 token 预算
    """

    transport: Transport
    """传输方式

    支持多传输方式的 provider 使用
    默认 "sse"
    """

    max_retry_delay_ms: int | None
    """最大重试延迟（毫秒）

    服务器请求长等待时，超过此值立即失败
    """

    tool_execution: ToolExecutionMode
    """工具执行模式

    - "sequential": 顺序执行
    - "parallel": 并行执行（默认）
    """

    before_tool_call: BeforeToolCallHook | None
    """工具执行前钩子

    用于权限检查、参数验证等
    """

    after_tool_call: AfterToolCallHook | None
    """工具执行后钩子

    用于结果修改、日志记录等
    """

    def __init__(
        self,
        initial_state: AgentState | None = None,
        convert_to_llm: Callable[[list[AgentMessage]], Awaitable[list[Any]]] | None = None,
        transform_context: Callable[[list[AgentMessage], Any], Awaitable[list[AgentMessage]]]
        | None = None,
        steering_mode: Literal["all", "one-at-a-time"] = "one-at-a-time",
        follow_up_mode: Literal["all", "one-at-a-time"] = "one-at-a-time",
        stream_fn: StreamFn | None = None,
        session_id: str | None = None,
        get_api_key: Callable[[str], Awaitable[str | None] | str | None] | None = None,
        on_payload: Any | None = None,
        thinking_budgets: ThinkingBudgets | None = None,
        transport: Transport = "sse",
        max_retry_delay_ms: int | None = None,
        tool_execution: ToolExecutionMode = "parallel",
        before_tool_call: BeforeToolCallHook | None = None,
        after_tool_call: AfterToolCallHook | None = None,
    ) -> None:
        """初始化配置选项

        参数：
            initial_state: 初始状态
            convert_to_llm: 消息转换函数
            transform_context: 上下文转换函数
            steering_mode: Steering 模式，默认 "one-at-a-time"
            follow_up_mode: Follow-up 模式，默认 "one-at-a-time"
            stream_fn: 自定义流式函数
            session_id: 会话 ID
            get_api_key: API Key 获取函数
            on_payload: Payload 检查函数
            thinking_budgets: 思考预算
            transport: 传输方式，默认 "sse"
            max_retry_delay_ms: 最大重试延迟
            tool_execution: 工具执行模式，默认 "parallel"
            before_tool_call: 工具前钩子
            after_tool_call: 工具后钩子
        """
        self.initial_state = initial_state
        self.convert_to_llm = convert_to_llm
        self.transform_context = transform_context
        self.steering_mode = steering_mode
        self.follow_up_mode = follow_up_mode
        self.stream_fn = stream_fn
        self.session_id = session_id
        self.get_api_key = get_api_key
        self.on_payload = on_payload
        self.thinking_budgets = thinking_budgets
        self.transport = transport
        self.max_retry_delay_ms = max_retry_delay_ms
        self.tool_execution = tool_execution
        self.before_tool_call = before_tool_call
        self.after_tool_call = after_tool_call


# ============================================================================
# Agent 类
# ============================================================================

from collections.abc import Awaitable, Callable
from typing import Literal


class Agent:
    """Agent 运行时类

    管理对话状态、工具执行、事件订阅等。这是用户代码的主要交互接口。

    生命周期：
        1. 创建：Agent(AgentOptions())
        2. 配置：set_model(), set_system_prompt(), set_tools()
        3. 交互：prompt() → 事件流 → wait_for_idle()
        4. 重复 3 进行多轮对话
        5. 重置：reset() 或创建新 Agent

    状态管理：
        - 对话历史保存在 state.messages
        - 系统提示保存在 state.system_prompt
        - 工具列表保存在 state.tools
        - 运行时状态：is_streaming, stream_message

    事件系统：
        - 通过 subscribe() 订阅事件
        - 事件类型：agent_start/end, turn_start/end, message_start/end/update
        - 用于 UI 更新、日志记录等

    消息队列：
        - steering_queue: 高优先级消息，中断当前执行
        - follow_up_queue: 低优先级消息，执行完成后处理

    示例：
        >>> # 基础用法
        >>> agent = Agent(AgentOptions(stream_fn=stream_fn))
        >>> agent.set_model(model)
        >>> agent.set_system_prompt("你是一个助手")
        >>>
        >>> # 多轮对话
        >>> await agent.prompt("你好，我叫小明")
        >>> await agent.wait_for_idle()
        >>> await agent.prompt("我叫什么名字？")  # Agent 记得"小明"
        >>> await agent.wait_for_idle()

        >>> # 带工具
        >>> agent.set_tools([FileReadTool(), FileWriteTool()])
        >>> await agent.prompt("读取 file.txt 并总结")
        >>> await agent.wait_for_idle()
    """

    def __init__(self, opts: AgentOptions | None = None) -> None:
        """初始化 Agent

        参数：
            opts: 配置选项，None 表示使用全部默认值

        示例：
            >>> # 默认配置
            >>> agent = Agent()

            >>> # 自定义配置
            >>> agent = Agent(AgentOptions(
            ...     stream_fn=custom_stream,
            ...     tool_execution="sequential"
            ... ))
        """
        opts = opts or AgentOptions()

        # 初始化状态
        self._state = opts.initial_state or AgentState()
        if not self._state.model:
            # 默认模型需要外部设置
            pass

        # 事件监听
        self._listeners: set[Callable[[AgentEvent], None]] = set()
        self._abort_controller: Any = None

        # 配置
        self._convert_to_llm = opts.convert_to_llm or self._default_convert_to_llm
        self._transform_context = opts.transform_context
        self._steering_mode = opts.steering_mode
        self._follow_up_mode = opts.follow_up_mode
        self._stream_fn = opts.stream_fn
        self._session_id = opts.session_id
        self._get_api_key = opts.get_api_key
        self._on_payload = opts.on_payload
        self._thinking_budgets = opts.thinking_budgets
        self._transport = opts.transport
        self._max_retry_delay_ms = opts.max_retry_delay_ms
        self._tool_execution = opts.tool_execution
        self._before_tool_call = opts.before_tool_call
        self._after_tool_call = opts.after_tool_call

        # 消息队列
        self._steering_queue: list[AgentMessage] = []
        self._follow_up_queue: list[AgentMessage] = []

        # 运行状态
        self._idle_event = asyncio.Event()
        self._idle_event.set()  # 初始状态为空闲

    # -------------------------------------------------------------------------
    # 属性访问
    # -------------------------------------------------------------------------

    @property
    def session_id(self) -> str | None:
        """当前会话 ID"""
        return self._session_id

    @session_id.setter
    def session_id(self, value: str | None) -> None:
        """设置会话 ID"""
        self._session_id = value

    @property
    def thinking_budgets(self) -> ThinkingBudgets | None:
        """思考预算配置"""
        return self._thinking_budgets

    @thinking_budgets.setter
    def thinking_budgets(self, value: ThinkingBudgets | None) -> None:
        """设置思考预算"""
        self._thinking_budgets = value

    @property
    def transport(self) -> Transport:
        """传输方式"""
        return cast(Transport, self._transport)

    def set_transport(self, value: Transport) -> None:
        """设置传输方式

        参数：
            value: 传输方式，如 "sse", "http"
        """
        self._transport = value

    @property
    def max_retry_delay_ms(self) -> int | None:
        """最大重试延迟（毫秒）"""
        return self._max_retry_delay_ms

    @max_retry_delay_ms.setter
    def max_retry_delay_ms(self, value: int | None) -> None:
        """设置最大重试延迟"""
        self._max_retry_delay_ms = value

    @property
    def tool_execution(self) -> ToolExecutionMode:
        """工具执行模式"""
        return cast(ToolExecutionMode, self._tool_execution)

    def set_tool_execution(self, value: ToolExecutionMode) -> None:
        """设置工具执行模式

        参数：
            value: "sequential" 或 "parallel"
        """
        self._tool_execution = value

    def set_before_tool_call(self, value: BeforeToolCallHook | None) -> None:
        """设置 beforeToolCall 钩子

        参数：
            value: 钩子函数或 None
        """
        self._before_tool_call = value

    def set_after_tool_call(self, value: AfterToolCallHook | None) -> None:
        """设置 afterToolCall 钩子

        参数：
            value: 钩子函数或 None
        """
        self._after_tool_call = value

    @property
    def state(self) -> AgentState:
        """当前状态

        包含完整的运行时状态：
        - messages: 对话历史
        - system_prompt: 系统提示
        - model: 当前模型
        - is_streaming: 是否正在生成
        """
        return self._state

    # -------------------------------------------------------------------------
    # 事件订阅
    # -------------------------------------------------------------------------

    def subscribe(self, fn: Callable[[AgentEvent], None]) -> Callable[[], None]:
        """订阅 Agent 事件

        订阅 Agent 的各种生命周期事件，用于 UI 更新、日志记录等。

        参数：
            fn: 事件处理函数，接收 AgentEvent 字典
                事件包含 type 字段标识事件类型

        返回：
            取消订阅函数，调用后不再接收事件

        事件类型：
            - agent_start: Agent 开始处理
            - agent_end: Agent 处理结束
            - turn_start: 新的 Turn 开始
            - turn_end: Turn 结束
            - message_start: 消息开始生成
            - message_update: 消息内容更新（流式）
            - message_end: 消息生成完成
            - tool_execution_start: 工具开始执行
            - tool_execution_end: 工具执行完成

        示例：
            >>> def on_event(event):
            ...     event_type = event.get("type")
            ...     if event_type == "message_end":
            ...         msg = event.get("message")
            ...         print(f"收到消息: {msg}")

            >>> unsubscribe = agent.subscribe(on_event)
            >>> # ... 使用 Agent
            >>> unsubscribe()  # 取消订阅
        """
        self._listeners.add(fn)

        def unsubscribe() -> None:
            self._listeners.discard(fn)

        return unsubscribe

    def _emit(self, event: AgentEvent) -> None:
        """发送事件到所有订阅者

        内部方法，由 Agent Loop 调用。

        参数：
            event: 事件字典
        """
        for listener in self._listeners:
            listener(event)

    # -------------------------------------------------------------------------
    # 状态修改
    # -------------------------------------------------------------------------

    def set_system_prompt(self, v: str) -> None:
        """设置系统提示

        系统提示定义助手的行为准则和能力范围。

        参数：
            v: 系统提示文本

        示例：
            >>> agent.set_system_prompt("你是一个 Python 专家")
            >>> agent.set_system_prompt(
            ...     "你是一个有帮助的助手。"
            ...     "回答要简洁，不超过 100 字。"
            ... )
        """
        self._state.system_prompt = v

    def set_model(self, m: Model) -> None:
        """设置模型

        设置用于生成回复的 LLM 模型。

        参数：
            m: 模型实例，通过 provider.get_model() 获取

        示例：
            >>> from ai.providers import KimiProvider
            >>> provider = KimiProvider()
            >>> agent.set_model(provider.get_model())
        """
        self._state.model = m

    def set_thinking_level(self, l: ThinkingLevel) -> None:
        """设置思考等级

        控制 LLM 的推理深度。

        参数：
            l: 思考等级
                - "off": 关闭思考
                - "minimal": 最小化
                - "low": 低深度
                - "medium": 中等（默认）
                - "high": 高深度
                - "xhigh": 极高深度

        示例：
            >>> agent.set_thinking_level("high")  # 复杂推理
            >>> agent.set_thinking_level("off")   # 快速回答
        """
        self._state.thinking_level = l

    def set_steering_mode(self, mode: Literal["all", "one-at-a-time"]) -> None:
        """设置 steering 模式

        控制 steering 消息的发送方式。

        参数：
            mode:
                - "all": 一次发送所有 steering 消息
                - "one-at-a-time": 每次只发送一条（默认）
        """
        self._steering_mode = mode

    def get_steering_mode(self) -> Literal["all", "one-at-a-time"]:
        """获取 steering 模式

        返回：
            当前 steering 模式
        """
        return cast(Literal["all", "one-at-a-time"], self._steering_mode)

    def set_follow_up_mode(self, mode: Literal["all", "one-at-a-time"]) -> None:
        """设置 follow-up 模式

        控制 follow-up 消息的发送方式。

        参数：
            mode:
                - "all": 一次发送所有 follow-up 消息
                - "one-at-a-time": 每次只发送一条（默认）
        """
        self._follow_up_mode = mode

    def get_follow_up_mode(self) -> Literal["all", "one-at-a-time"]:
        """获取 follow-up 模式

        返回：
            当前 follow-up 模式
        """
        return cast(Literal["all", "one-at-a-time"], self._follow_up_mode)

    def set_tools(self, t: list[AgentTool]) -> None:
        """设置工具列表

        设置 Agent 可调用的工具。

        参数：
            t: AgentTool 实例列表

        示例：
            >>> agent.set_tools([
            ...     FileReadTool(),
            ...     FileWriteTool(),
            ...     BashTool()
            ... ])
        """
        self._state.tools = t

    def replace_messages(self, ms: list[AgentMessage]) -> None:
        """替换消息列表

        完全替换当前对话历史。用于加载历史会话或重置对话。

        参数：
            ms: 新的消息列表

        示例：
            >>> # 加载历史会话
            >>> history = load_conversation("session_123")
            >>> agent.replace_messages(history)
        """
        self._state.messages = ms[:]

    def append_message(self, m: AgentMessage) -> None:
        """追加消息

        向对话历史追加单条消息。

        参数：
            m: 要追加的消息

        示例：
            >>> from ai.types import UserMessage
            >>> agent.append_message(UserMessage(text="用户消息"))
        """
        self._state.messages = [*self._state.messages, m]

    # -------------------------------------------------------------------------
    # 消息队列管理
    # -------------------------------------------------------------------------

    def steer(self, m: AgentMessage) -> None:
        """排队 steering 消息（中断当前执行）

        将消息加入 steering 队列。如果 Agent 正在执行，
        这条消息会在当前 turn 结束后优先处理。

        适用场景：
        - 用户打断："不用继续了，直接告诉我结论"
        - 系统干预：注入系统消息

        参数：
            m: 要 steering 的消息

        示例：
            >>> from ai.types import UserMessage
            >>>
            >>> # 用户正在询问复杂问题
            >>> await agent.prompt("详细解释量子力学")
            >>>
            >>> # 用户改变主意
            >>> agent.steer(UserMessage(text="不用详细了，一句话总结"))
            >>> await agent.wait_for_idle()
        """
        self._steering_queue.append(m)

    def follow_up(self, m: AgentMessage) -> None:
        """排队 follow-up 消息（执行完成后处理）

        将消息加入 follow-up 队列。这条消息会在当前执行
        完全结束后处理。

        适用场景：
        - 自动追问：根据上下文生成后续问题
        - 任务链：分解复杂任务

        参数：
            m: 要 follow-up 的消息

        示例：
            >>> # 在回调中添加 follow-up
            >>> def on_event(event):
            ...     if event.get("type") == "agent_end":
            ...         # 任务完成，自动追问
            ...         agent.follow_up(UserMessage(text="还有其他问题吗？"))
        """
        self._follow_up_queue.append(m)

    def clear_steering_queue(self) -> None:
        """清空 steering 队列"""
        self._steering_queue = []

    def clear_follow_up_queue(self) -> None:
        """清空 follow-up 队列"""
        self._follow_up_queue = []

    def clear_all_queues(self) -> None:
        """清空所有队列"""
        self._steering_queue = []
        self._follow_up_queue = []

    def has_queued_messages(self) -> bool:
        """是否有排队的消息

        返回：
            True 如果有 steering 或 follow-up 消息
        """
        return len(self._steering_queue) > 0 or len(self._follow_up_queue) > 0

    def _dequeue_steering_messages(self) -> list[AgentMessage]:
        """取出 steering 消息

        根据 steering_mode 决定返回一条还是全部。

        返回：
            要处理的 steering 消息列表
        """
        if self._steering_mode == "one-at-a-time":
            if self._steering_queue:
                first = self._steering_queue[0]
                self._steering_queue = self._steering_queue[1:]
                return [first]
            return []

        steering = self._steering_queue[:]
        self._steering_queue = []
        return steering

    def _dequeue_follow_up_messages(self) -> list[AgentMessage]:
        """取出 follow-up 消息

        根据 follow_up_mode 决定返回一条还是全部。

        返回：
            要处理的 follow-up 消息列表
        """
        if self._follow_up_mode == "one-at-a-time":
            if self._follow_up_queue:
                first = self._follow_up_queue[0]
                self._follow_up_queue = self._follow_up_queue[1:]
                return [first]
            return []

        follow_up = self._follow_up_queue[:]
        self._follow_up_queue = []
        return follow_up

    def clear_messages(self) -> None:
        """清空消息列表"""
        self._state.messages = []

    def abort(self) -> None:
        """中止当前执行"""
        if self._abort_controller:
            # 取消操作
            pass

    async def wait_for_idle(self) -> None:
        """等待当前执行完成

        阻塞直到当前 prompt() 或 continue_() 完成。
        用于确保在发送新消息前上一消息已处理完毕。

        示例：
            >>> await agent.prompt("你好")
            >>> await agent.wait_for_idle()  # 确保完成
            >>> print(f"对话历史: {len(agent.state.messages)} 条")
        """
        await self._idle_event.wait()

    def reset(self) -> None:
        """重置 Agent 状态

        清空所有状态，相当于创建新 Agent。
        保留配置（模型、工具等），仅重置运行时状态。

        示例：
            >>> # 结束当前对话，开始新对话
            >>> agent.reset()
            >>> assert len(agent.state.messages) == 0
        """
        self._state.messages = []
        self._state.is_streaming = False
        self._state.stream_message = None
        self._state.pending_tool_calls = set()
        self._state.error = None
        self._steering_queue = []
        self._follow_up_queue = []

    # -------------------------------------------------------------------------
    # 主要接口
    # -------------------------------------------------------------------------

    async def prompt(
        self,
        input_val: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ) -> None:
        """发送提示

        向 Agent 发送用户输入，触发 LLM 生成回复。

        参数：
            input_val:
                - str: 用户文本消息
                - AgentMessage: 单条消息对象
                - list[AgentMessage]: 多条消息列表
            images: 图像内容列表（仅当 input_val 为 str 时有效）

        异常：
            RuntimeError: 如果 Agent 正在处理其他消息
            RuntimeError: 如果没有配置模型

        说明：
            - 此方法立即返回，不等待生成完成
            - 使用 wait_for_idle() 等待完成
            - 通过 subscribe() 订阅事件获取进度

        示例：
            >>> # 发送文本
            >>> await agent.prompt("你好！")

            >>> # 发送带图片的消息
            >>> from ai.types import ImageContent
            >>> image = ImageContent(mime_type="image/png", data=base64_data)
            >>> await agent.prompt("描述这张图片", images=[image])

            >>> # 发送消息对象
            >>> from ai.types import UserMessage
            >>> await agent.prompt(UserMessage(text="你好"))
        """
        if self._state.is_streaming:
            raise RuntimeError(
                "Agent is already processing a prompt. Use steer() or followUp() "
                "to queue messages, or wait for completion."
            )

        model = self._state.model
        if not model:
            raise RuntimeError("No model configured")

        msgs: list[AgentMessage]

        if isinstance(input_val, list):
            msgs = input_val
        elif isinstance(input_val, str):
            content: list[TextContent | ImageContent] = [TextContent(text=input_val)]
            if images:
                content.extend(images)

            from ai.types import UserMessage

            msgs = [UserMessage(content=content)]
        else:
            msgs = [input_val]

        await self._run_loop(msgs)

    async def continue_(self) -> None:
        """从当前上下文继续

        在当前对话上下文中继续，不添加新消息。
        用于：
        - 重试失败的请求
        - 在 steering/follow-up 后继续
        - 处理工具调用后的继续

        异常：
            RuntimeError: 如果对话为空
            RuntimeError: 如果最后消息是 assistant（应使用 steer/follow_up）

        说明：
            - 最后消息必须是 user 或 toolResult
            - 如果最后消息是 assistant，需要使用其他方法

        示例：
            >>> # 通常在循环或回调中使用
            >>> def on_event(event):
            ...     if event.get("type") == "turn_end":
            ...         # 处理 turn 结束后的逻辑
            ...         pass
        """
        if self._state.is_streaming:
            raise RuntimeError(
                "Agent is already processing. Wait for completion before continuing."
            )

        messages = self._state.messages
        if not messages:
            raise RuntimeError("No messages to continue from")

        last = messages[-1]
        if last.role == "assistant":  # type: ignore[attr-defined]
            queued_steering = self._dequeue_steering_messages()
            if queued_steering:
                await self._run_loop(queued_steering, skip_initial_steering_poll=True)
                return

            queued_follow_up = self._dequeue_follow_up_messages()
            if queued_follow_up:
                await self._run_loop(queued_follow_up)
                return

            raise RuntimeError("Cannot continue from message role: assistant")

        await self._run_loop(None)

    # -------------------------------------------------------------------------
    # 内部实现
    # -------------------------------------------------------------------------

    async def _run_loop(
        self,
        messages: list[AgentMessage] | None,
        skip_initial_steering_poll: bool = False,
    ) -> None:
        """运行 Agent Loop（内部方法）

        启动 Agent Loop 处理消息。

        参数：
            messages: 要处理的消息，None 表示继续当前上下文
            skip_initial_steering_poll: 是否跳过初始 steering 检查
        """
        model = self._state.model
        if not model:
            raise RuntimeError("No model configured")

        # 标记为忙碌状态
        self._idle_event.clear()

        self._state.is_streaming = True
        self._state.stream_message = None
        self._state.error = None

        # 推理设置

        # 构建上下文
        context = AgentContext(
            system_prompt=self._state.system_prompt,
            messages=self._state.messages[:],
            tools=self._state.tools,
        )

        skip_steering = skip_initial_steering_poll

        # 构建配置
        config = AgentLoopConfig(
            model=model,
            convert_to_llm=self._convert_to_llm,  # type: ignore[arg-type]
            transform_context=self._transform_context,
            get_api_key=self._get_api_key,  # type: ignore[arg-type]
            tool_execution=cast(ToolExecutionMode, self._tool_execution),
            before_tool_call=self._before_tool_call,
            after_tool_call=self._after_tool_call,
        )

        # 设置 steering 回调
        async def get_steering() -> list[AgentMessage]:
            nonlocal skip_steering
            if skip_steering:
                skip_steering = False
                return []
            return self._dequeue_steering_messages()

        config.get_steering_messages = get_steering

        async def get_follow_up() -> list[AgentMessage]:
            return self._dequeue_follow_up_messages()

        config.get_follow_up_messages = get_follow_up

        try:
            if messages:
                await run_agent_loop(
                    messages,
                    context,
                    config,
                    self._process_loop_event,
                    None,
                    self._stream_fn,
                )
            else:
                await run_agent_loop_continue(
                    context,
                    config,
                    self._process_loop_event,
                    None,
                    self._stream_fn,
                )
        except Exception as err:
            await self._handle_error(err, model)
        finally:
            self._state.is_streaming = False
            self._state.stream_message = None
            self._state.pending_tool_calls = set()
            self._abort_controller = None
            self._idle_event.set()  # 标记为空闲状态

    def _process_loop_event(self, event: AgentEvent) -> None:
        """处理 Loop 事件并更新状态（内部方法）

        将 Loop 事件转换为状态更新，并广播给订阅者。

        参数：
            event: 事件字典
        """
        event_type = event.get("type", "")

        if event_type == "message_start" or event_type == "message_update":
            self._state.stream_message = event.get("message")

        elif event_type == "message_end":
            self._state.stream_message = None
            msg = event.get("message")
            if msg:
                self.append_message(msg)

        elif event_type == "tool_execution_start":
            tool_call_id = event.get("toolCallId", "")
            if tool_call_id:
                self._state.pending_tool_calls.add(tool_call_id)

        elif event_type == "tool_execution_end":
            tool_call_id = event.get("toolCallId", "")
            if tool_call_id:
                self._state.pending_tool_calls.discard(tool_call_id)

        elif event_type == "turn_end":
            msg = event.get("message")
            if msg and isinstance(msg, AssistantMessage) and msg.error_message:
                self._state.error = msg.error_message

        elif event_type == "agent_end":
            self._state.is_streaming = False
            self._state.stream_message = None

        self._emit(event)

    async def _handle_error(self, err: Exception, model: Model) -> None:
        """处理执行错误（内部方法）

        将错误封装为错误消息并添加到对话历史。

        参数：
            err: 异常对象
            model: 当前模型
        """
        import time

        error_msg: AgentMessage = {
            "role": "assistant",  # type: ignore[dict-item]
            "content": [{"type": "text", "text": ""}],
            "api": model.api,
            "provider": model.provider,
            "model": model.id,
            "usage": {
                "input": 0,
                "output": 0,
                "cache_read": 0,
                "cache_write": 0,
                "total_tokens": 0,
                "cost": {
                    "input": 0.0,
                    "output": 0.0,
                    "cache_read": 0.0,
                    "cache_write": 0.0,
                    "total": 0.0,
                },
            },
            "stop_reason": "aborted" if self._abort_controller else "error",
            "error_message": str(err),
            "timestamp": int(time.time() * 1000),
        }

        self.append_message(error_msg)
        self._state.error = str(err)
        self._emit({"type": "agent_end", "messages": [error_msg]})

    @staticmethod
    async def _default_convert_to_llm(messages: list[AgentMessage]) -> list[Any]:
        """默认消息转换：过滤出 LLM 兼容的消息

        保留 role 为 user、assistant、toolResult 的消息。

        参数：
            messages: AgentMessage 列表

        返回：
            LLM 兼容的消息列表
        """
        result: list[Any] = []
        for m in messages:
            if m.role in ("user", "assistant", "toolResult"):  # type: ignore[attr-defined]
                result.append(m)
        return result
