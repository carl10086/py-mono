"""
Agent 运行时模块 - 对齐 pi-mono 架构

导出所有公共类型和类：
- Agent 类: 高层 Agent 接口
- AgentLoop: 核心循环函数
- 类型定义: AgentTool, AgentEvent, AgentState 等
"""

from __future__ import annotations

# Agent 类
from agent.agent import Agent, AgentOptions

# Agent Loop
from agent.agent_loop import run_agent_loop, run_agent_loop_continue

# 类型定义
from agent.types import (
    # Hook 类型
    AfterToolCallContext,
    AfterToolCallHook,
    AfterToolCallResult,
    # Agent 类型
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentState,
    AgentTool,
    AgentToolCall,
    AgentToolResult,
    AgentToolUpdateCallback,
    BeforeToolCallContext,
    BeforeToolCallHook,
    BeforeToolCallResult,
    # 基础类型
    StreamFn,
    ThinkingLevel,
    ToolExecutionMode,
)

__version__ = "0.1.0"

__all__ = [
    # Agent 类
    "Agent",
    "AgentOptions",
    # Loop 函数
    "run_agent_loop",
    "run_agent_loop_continue",
    # 核心类型
    "AgentTool",
    "AgentToolCall",
    "AgentToolResult",
    "AgentToolUpdateCallback",
    "AgentContext",
    "AgentMessage",
    "AgentState",
    "AgentEvent",
    "AgentLoopConfig",
    # Hook 类型
    "BeforeToolCallContext",
    "BeforeToolCallResult",
    "BeforeToolCallHook",
    "AfterToolCallContext",
    "AfterToolCallResult",
    "AfterToolCallHook",
    # 基础类型
    "StreamFn",
    "ThinkingLevel",
    "ToolExecutionMode",
]
