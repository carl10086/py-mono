# Pi-Mono Python 复刻方案

## 背景与目标

基于 pi-mono 项目（TypeScript AI Agent 架构）复刻一个高质量的 Python 版本，结合 kimi-cli 的技术实现模式。

**核心要求**:
- Python 3.12+ (使用最新 3.14)
- 仅支持 Anthropic 模型
- 严格类型检查（pyright strict mode）
- 分层架构：AI Core → Agent Runtime → Application

---

## 架构设计

### 1. 整体结构

```
packages/
├── ai/                          # AI 核心层（对标 pi-mono/packages/ai）
│   ├── src/ai/
│   │   ├── __init__.py
│   │   ├── types.py            # 核心类型定义（Message, Tool, Model, Context）
│   │   ├── registry.py         # Provider 注册表
│   │   ├── stream.py           # 流式处理
│   │   ├── models.py           # 模型定义与管理
│   │   └── providers/
│   │       ├── __init__.py
│   │       └── anthropic.py    # Anthropic Provider 实现
│   └── tests/
│
├── agent/                       # Agent 运行时（对标 pi-mono/packages/agent）
│   ├── src/agent/
│   │   ├── __init__.py
│   │   ├── agent.py            # Agent 主类
│   │   ├── loop.py             # Agent 执行循环
│   │   ├── types.py            # Agent 类型定义（AgentTool, AgentEvent）
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── base.py         # 工具基类
│   │       ├── bash.py         # Bash 工具
│   │       ├── read.py         # 文件读取
│   │       ├── write.py        # 文件写入
│   │       ├── edit.py         # 文件编辑
│   │       ├── grep.py         # 文本搜索
│   │       ├── find.py         # 文件查找
│   │       └── ls.py           # 目录列表
│   └── tests/
│
└── cli/                         # CLI 应用层（对标 coding-agent）
    ├── src/cli/
    │   ├── __init__.py
    │   ├── main.py             # 入口点
    │   ├── config.py           # 配置管理
    │   ├── session.py          # Session 管理
    │   └── ui.py               # 交互式 UI
    └── tests/
```

### 2. 包依赖关系

```
cli → agent → ai
```

**pyproject.toml 配置**:
- 使用 uv workspace
- ai: 无内部依赖
- agent: 依赖 ai (workspace)
- cli: 依赖 agent (workspace)

---

## 核心模块设计

### 2.1 AI 核心层 (packages/ai)

#### 2.1.1 类型系统 (types.py)

```python
from typing import Literal, TypedDict, NotRequired
from pydantic import BaseModel

# 消息类型
class TextContent(TypedDict):
    type: Literal["text"]
    text: str

class ImageContent(TypedDict):
    type: Literal["image"]
    source: str  # base64 or url
    mime_type: str

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict  # JSON parsed

class UserMessage(BaseModel):
    role: Literal["user"]
    content: list[TextContent | ImageContent]

class AssistantMessage(BaseModel):
    role: Literal["assistant"]
    content: list[TextContent]
    tool_calls: list[ToolCall] | None = None
    thinking: str | None = None  # Anthropic thinking

class ToolResultMessage(BaseModel):
    role: Literal["tool"]
    tool_call_id: str
    content: str
    is_error: bool = False

Message = UserMessage | AssistantMessage | ToolResultMessage

# 工具定义
class ToolParameter(BaseModel):
    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = True
    enum: list[str] | None = None

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: list[ToolParameter]

# 上下文
class Context(BaseModel):
    system_prompt: str | None = None
    messages: list[Message]
    tools: list[ToolDefinition] | None = None

# 模型定义
class Model(BaseModel):
    id: str
    name: str
    provider: str
    context_window: int
    max_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    supports_thinking: bool = False
```

#### 2.1.2 Provider 注册表 (registry.py)

```python
from typing import Protocol, Callable, AsyncIterator, runtime_checkable
from .types import Context, AssistantMessage, ToolResultMessage

# 流事件类型
StreamEvent = (
    {"type": "start"}
    | {"type": "content"; "delta": str}
    | {"type": "thinking"; "delta": str}
    | {"type": "tool_call"; "tool_call": ToolCall}
    | {"type": "done"; "message": AssistantMessage}
    | {"type": "error"; "error": str}
)

@runtime_checkable
class Provider(Protocol):
    """Provider 接口协议"""

    @property
    def name(self) -> str:
        """Provider 名称"""
        ...

    async def stream(
        self,
        context: Context,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """流式生成响应"""
        ...

    def get_model(self, model_id: str) -> Model:
        """获取模型配置"""
        ...

# 全局注册表
_providers: dict[str, Provider] = {}

def register_provider(name: str, provider: Provider) -> None:
    """注册 Provider"""
    _providers[name] = provider

def get_provider(name: str) -> Provider:
    """获取 Provider"""
    if name not in _providers:
        raise ValueError(f"Unknown provider: {name}")
    return _providers[name]

def list_providers() -> list[str]:
    """列出所有已注册 Provider"""
    return list(_providers.keys())
```

#### 2.1.3 Anthropic Provider (providers/anthropic.py)

```python
from anthropic import AsyncAnthropic
from anthropic.types import MessageStreamEvent
from ..registry import register_provider
from ..types import (
    Context, AssistantMessage, ToolCall, ToolResultMessage,
    TextContent, UserMessage, Model
)

ANTHROPIC_MODELS = {
    "claude-opus-4": Model(
        id="claude-opus-4",
        name="Claude Opus 4",
        provider="anthropic",
        context_window=200000,
        max_tokens=4096,
        cost_per_1k_input=15.0,
        cost_per_1k_output=75.0,
        supports_thinking=True,
    ),
    "claude-sonnet-4": Model(
        id="claude-sonnet-4",
        name="Claude Sonnet 4",
        provider="anthropic",
        context_window=200000,
        max_tokens=8192,
        cost_per_1k_input=3.0,
        cost_per_1k_output=15.0,
        supports_thinking=False,
    ),
}

class AnthropicProvider:
    """Anthropic Provider 实现"""

    name = "anthropic"

    def __init__(self) -> None:
        self._client: AsyncAnthropic | None = None

    def _get_client(self, api_key: str | None, base_url: str | None) -> AsyncAnthropic:
        if self._client is None:
            self._client = AsyncAnthropic(
                api_key=api_key,
                base_url=base_url,
            )
        return self._client

    async def stream(
        self,
        context: Context,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> AsyncIterator[StreamEvent]:
        client = self._get_client(api_key, base_url)

        # 转换消息格式
        messages = self._convert_messages(context.messages)
        tools = self._convert_tools(context.tools) if context.tools else None

        async with client.messages.stream(
            model=context.model or "claude-sonnet-4",
            max_tokens=4096,
            system=context.system_prompt,
            messages=messages,
            tools=tools,
        ) as stream:
            async for event in stream:
                yield self._convert_event(event)

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """转换内部消息格式为 Anthropic 格式"""
        result = []
        for msg in messages:
            if isinstance(msg, UserMessage):
                result.append({
                    "role": "user",
                    "content": [{"type": "text", "text": c["text"]}
                               for c in msg.content]
                })
            elif isinstance(msg, AssistantMessage):
                content = [{"type": "text", "text": c["text"]}
                          for c in msg.content]
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        content.append({
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.arguments
                        })
                result.append({"role": "assistant", "content": content})
            elif isinstance(msg, ToolResultMessage):
                result.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content,
                        "is_error": msg.is_error
                    }]
                })
        return result

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict]:
        """转换工具定义为 Anthropic 格式"""
        return [{
            "name": t.name,
            "description": t.description,
            "input_schema": self._convert_parameters(t.parameters)
        } for t in tools]

    def _convert_parameters(self, params: list[ToolParameter]) -> dict:
        """转换参数定义为 JSON Schema"""
        properties = {}
        required = []
        for p in params:
            properties[p.name] = {
                "type": p.type,
                "description": p.description,
            }
            if p.enum:
                properties[p.name]["enum"] = p.enum
            if p.required:
                required.append(p.name)
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def _convert_event(self, event: MessageStreamEvent) -> StreamEvent:
        """转换 Anthropic 事件为内部事件"""
        # 实现事件转换逻辑
        ...

    def get_model(self, model_id: str) -> Model:
        if model_id not in ANTHROPIC_MODELS:
            raise ValueError(f"Unknown model: {model_id}")
        return ANTHROPIC_MODELS[model_id]

# 注册 Provider
register_provider("anthropic", AnthropicProvider())
```

### 2.2 Agent 运行时 (packages/agent)

#### 2.2.1 Agent 类型定义 (types.py)

```python
from enum import Enum, auto
from typing import Protocol, Callable, Awaitable, AsyncIterator
from pydantic import BaseModel
from ai.types import ToolDefinition, Message, AssistantMessage, ToolResultMessage

class AgentEventType(Enum):
    # Agent 生命周期
    AGENT_START = auto()
    AGENT_END = auto()

    # Turn 生命周期（一次助手响应 + 工具调用）
    TURN_START = auto()
    TURN_END = auto()

    # 消息生命周期
    MESSAGE_START = auto()
    MESSAGE_UPDATE = auto()
    MESSAGE_END = auto()

    # 工具执行生命周期
    TOOL_EXECUTION_START = auto()
    TOOL_EXECUTION_UPDATE = auto()
    TOOL_EXECUTION_END = auto()

class AgentEvent(BaseModel):
    type: AgentEventType
    data: dict

# 工具结果
class ToolResult(BaseModel):
    content: str
    is_error: bool = False
    data: dict | None = None  # 额外数据用于 UI 展示

# 工具接口
class AgentTool(Protocol):
    """Agent 工具接口"""

    @property
    def definition(self) -> ToolDefinition:
        """工具定义（用于 LLM）"""
        ...

    async def execute(
        self,
        tool_call_id: str,
        arguments: dict,
        signal: Any | None = None,
    ) -> ToolResult:
        """执行工具"""
        ...

# Agent 配置
class AgentConfig(BaseModel):
    model: str = "claude-sonnet-4"
    system_prompt: str = ""
    tools: list[AgentTool] = []
    max_turns: int = 50  # 防止无限循环
    api_key: str | None = None

    # 钩子函数
    before_tool_call: Callable[[str, dict], Awaitable[None]] | None = None
    after_tool_call: Callable[[str, ToolResult], Awaitable[None]] | None = None
```

#### 2.2.2 Agent 主类 (agent.py)

```python
import asyncio
from typing import AsyncIterator, Callable
from ai import get_provider
from ai.types import (
    Context, UserMessage, AssistantMessage, ToolResultMessage,
    ToolCall, TextContent
)
from .types import AgentConfig, AgentTool, AgentEvent, AgentEventType, ToolResult
from .loop import AgentLoop

class Agent:
    """Agent 主类 - 管理对话状态和执行"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self._messages: list[Message] = []
        self._provider = get_provider("anthropic")
        self._loop = AgentLoop(self)
        self._event_handlers: list[Callable[[AgentEvent], None]] = []
        self._is_running = False

    def on_event(self, handler: Callable[[AgentEvent], None]) -> None:
        """订阅事件"""
        self._event_handlers.append(handler)

    def _emit(self, event: AgentEvent) -> None:
        """发送事件"""
        for handler in self._event_handlers:
            handler(event)

    async def prompt(self, message: str | UserMessage) -> None:
        """发送用户消息并执行"""
        if isinstance(message, str):
            message = UserMessage(
                role="user",
                content=[TextContent(type="text", text=message)]
            )

        self._messages.append(message)
        await self._run_loop()

    async def _run_loop(self) -> None:
        """运行 Agent 循环"""
        if self._is_running:
            return

        self._is_running = True
        self._emit(AgentEvent(type=AgentEventType.AGENT_START, data={}))

        try:
            await self._loop.run()
        finally:
            self._is_running = False
            self._emit(AgentEvent(
                type=AgentEventType.AGENT_END,
                data={"messages": self._messages}
            ))

    def get_context(self) -> Context:
        """获取当前上下文"""
        tool_definitions = [
            tool.definition for tool in self.config.tools
        ] if self.config.tools else None

        return Context(
            system_prompt=self.config.system_prompt,
            messages=self._messages.copy(),
            tools=tool_definitions,
        )

    async def execute_tool(self, tool_call: ToolCall) -> ToolResultMessage:
        """执行工具调用"""
        # 查找工具
        tool = None
        for t in self.config.tools:
            if t.definition.name == tool_call.name:
                tool = t
                break

        if tool is None:
            return ToolResultMessage(
                role="tool",
                tool_call_id=tool_call.id,
                content=f"Tool not found: {tool_call.name}",
                is_error=True
            )

        # 执行前钩子
        if self.config.before_tool_call:
            await self.config.before_tool_call(tool_call.name, tool_call.arguments)

        self._emit(AgentEvent(
            type=AgentEventType.TOOL_EXECUTION_START,
            data={
                "tool_call_id": tool_call.id,
                "tool_name": tool_call.name,
                "arguments": tool_call.arguments
            }
        ))

        try:
            result = await tool.execute(
                tool_call_id=tool_call.id,
                arguments=tool_call.arguments
            )

            self._emit(AgentEvent(
                type=AgentEventType.TOOL_EXECUTION_END,
                data={
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_call.name,
                    "result": result
                }
            ))

            # 执行后钩子
            if self.config.after_tool_call:
                await self.config.after_tool_call(tool_call.name, result)

            return ToolResultMessage(
                role="tool",
                tool_call_id=tool_call.id,
                content=result.content,
                is_error=result.is_error
            )

        except Exception as e:
            error_msg = f"Tool execution error: {str(e)}"
            self._emit(AgentEvent(
                type=AgentEventType.TOOL_EXECUTION_END,
                data={
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_call.name,
                    "error": error_msg
                }
            ))
            return ToolResultMessage(
                role="tool",
                tool_call_id=tool_call.id,
                content=error_msg,
                is_error=True
            )

    def append_message(self, message: Message) -> None:
        """添加消息到历史"""
        self._messages.append(message)

    @property
    def messages(self) -> list[Message]:
        """获取消息历史"""
        return self._messages.copy()
```

#### 2.2.3 Agent 循环 (loop.py)

```python
from ai.types import AssistantMessage, ToolCall
from .types import AgentEventType

class AgentLoop:
    """Agent 执行循环"""

    def __init__(self, agent: "Agent"):
        self.agent = agent
        self._turn_count = 0

    async def run(self) -> None:
        """运行循环直到没有更多工具调用或达到最大轮数"""
        while self._turn_count < self.agent.config.max_turns:
            self.agent._emit(AgentEvent(
                type=AgentEventType.TURN_START,
                data={"turn": self._turn_count}
            ))

            # 获取上下文
            context = self.agent.get_context()

            # 调用 LLM
            assistant_message = await self._call_llm(context)

            if assistant_message is None:
                break

            # 添加到历史
            self.agent.append_message(assistant_message)

            # 处理工具调用
            if assistant_message.tool_calls:
                tool_results = await self._execute_tool_calls(
                    assistant_message.tool_calls
                )
                for result in tool_results:
                    self.agent.append_message(result)
            else:
                # 没有工具调用，结束本轮
                self.agent._emit(AgentEvent(
                    type=AgentEventType.TURN_END,
                    data={"message": assistant_message}
                ))
                break

            self._turn_count += 1

    async def _call_llm(self, context: Context) -> AssistantMessage | None:
        """调用 LLM 获取响应"""
        # 收集完整响应
        content_parts = []
        tool_calls = []
        thinking = None

        async for event in self.agent._provider.stream(
            context,
            api_key=self.agent.config.api_key
        ):
            if event["type"] == "content":
                content_parts.append(event["delta"])
            elif event["type"] == "thinking":
                if thinking is None:
                    thinking = ""
                thinking += event["delta"]
            elif event["type"] == "tool_call":
                tool_calls.append(event["tool_call"])
            elif event["type"] == "done":
                return event["message"]
            elif event["type"] == "error":
                # 处理错误
                return None

        # 构建消息（如果没有 done 事件）
        return AssistantMessage(
            role="assistant",
            content=[{"type": "text", "text": "".join(content_parts)}],
            tool_calls=tool_calls if tool_calls else None,
            thinking=thinking
        )

    async def _execute_tool_calls(
        self,
        tool_calls: list[ToolCall]
    ) -> list[ToolResultMessage]:
        """执行工具调用（并行）"""
        tasks = [
            self.agent.execute_tool(tc)
            for tc in tool_calls
        ]
        return await asyncio.gather(*tasks)
```

### 2.3 工具实现 (packages/agent/tools)

#### 2.3.1 工具基类 (base.py)

```python
from abc import ABC, abstractmethod
from ..types import AgentTool, ToolDefinition, ToolResult

class BaseTool(ABC, AgentTool):
    """工具基类"""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """工具定义"""
        pass

    @abstractmethod
    async def execute(
        self,
        tool_call_id: str,
        arguments: dict,
        signal: Any | None = None
    ) -> ToolResult:
        """执行工具"""
        pass
```

#### 2.3.2 Bash 工具 (bash.py)

```python
import asyncio
from .base import BaseTool
from ..types import ToolDefinition, ToolParameter, ToolResult

class BashTool(BaseTool):
    """Bash 命令执行工具"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="bash",
            description="Execute bash commands in the shell",
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="The bash command to execute",
                    required=True
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout in seconds (default: 60)",
                    required=False
                ),
                ToolParameter(
                    name="working_dir",
                    type="string",
                    description="Working directory for the command",
                    required=False
                )
            ]
        )

    async def execute(
        self,
        tool_call_id: str,
        arguments: dict,
        signal: Any | None = None
    ) -> ToolResult:
        command = arguments["command"]
        timeout = arguments.get("timeout", 60)
        working_dir = arguments.get("working_dir")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            output = stdout.decode()
            if stderr:
                output += f"\n[stderr]\n{stderr.decode()}"

            return ToolResult(
                content=output or "(no output)",
                is_error=process.returncode != 0,
                data={"returncode": process.returncode}
            )

        except asyncio.TimeoutError:
            process.kill()
            return ToolResult(
                content=f"Command timed out after {timeout} seconds",
                is_error=True
            )
        except Exception as e:
            return ToolResult(
                content=f"Error: {str(e)}",
                is_error=True
            )
```

#### 2.3.3 文件工具 (read.py, write.py, edit.py)

```python
# read.py
import aiofiles
from pathlib import Path
from .base import BaseTool

class ReadFileTool(BaseTool):
    """读取文件工具"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_file",
            description="Read the contents of a file",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file",
                    required=True
                ),
                ToolParameter(
                    name="offset",
                    type="integer",
                    description="Line offset to start reading from",
                    required=False
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Maximum number of lines to read",
                    required=False
                )
            ]
        )

    async def execute(self, tool_call_id: str, arguments: dict, signal=None) -> ToolResult:
        path = Path(arguments["path"])
        offset = arguments.get("offset", 0)
        limit = arguments.get("limit")

        try:
            async with aiofiles.open(path, 'r') as f:
                lines = await f.readlines()

                start = offset
                end = offset + limit if limit else len(lines)
                selected_lines = lines[start:end]

                content = "".join(selected_lines)

                return ToolResult(
                    content=content,
                    data={
                        "total_lines": len(lines),
                        "returned_lines": len(selected_lines),
                        "offset": offset
                    }
                )
        except Exception as e:
            return ToolResult(content=str(e), is_error=True)

# write.py
class WriteFileTool(BaseTool):
    """写入文件工具"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_file",
            description="Write content to a file (creates or overwrites)",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write",
                    required=True
                )
            ]
        )

    async def execute(self, tool_call_id: str, arguments: dict, signal=None) -> ToolResult:
        path = Path(arguments["path"])
        content = arguments["content"]

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(path, 'w') as f:
                await f.write(content)

            return ToolResult(content=f"File written successfully: {path}")
        except Exception as e:
            return ToolResult(content=str(e), is_error=True)
```

### 2.4 CLI 应用层 (packages/cli)

#### 2.4.1 配置管理 (config.py)

```python
from pydantic import BaseModel, Field
from pathlib import Path

class CLIConfig(BaseModel):
    """CLI 配置"""
    default_model: str = "claude-sonnet-4"
    api_key: str | None = None
    base_url: str | None = None
    max_turns: int = 50
    working_dir: Path = Field(default_factory=lambda: Path.cwd())

    # 工具配置
    enable_bash: bool = True
    enable_file_tools: bool = True
    enable_search_tools: bool = True

    @classmethod
    def load(cls, path: Path | None = None) -> "CLIConfig":
        """从文件加载配置"""
        if path is None:
            path = Path.home() / ".config" / "pyai" / "config.toml"

        if not path.exists():
            return cls()

        import tomllib
        with open(path, "rb") as f:
            data = tomllib.load(f)

        return cls(**data)

    def save(self, path: Path | None = None) -> None:
        """保存配置到文件"""
        if path is None:
            path = Path.home() / ".config" / "pyai" / "config.toml"

        path.parent.mkdir(parents=True, exist_ok=True)

        import tomli_w
        with open(path, "wb") as f:
            tomli_w.dump(self.model_dump(), f)
```

#### 2.4.2 Session 管理 (session.py)

```python
import json
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
from agent import Agent, AgentConfig
from ai.types import Message

class Session(BaseModel):
    """对话 Session"""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    messages: list[Message]
    config: AgentConfig

    class Config:
        arbitrary_types_allowed = True

class SessionManager:
    """Session 管理器"""

    def __init__(self, storage_dir: Path | None = None):
        if storage_dir is None:
            storage_dir = Path.home() / ".config" / "pyai" / "sessions"
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, session: Session) -> None:
        """保存 Session"""
        path = self.storage_dir / f"{session.id}.json"
        with open(path, "w") as f:
            json.dump(session.model_dump(), f, default=str, indent=2)

    def load_session(self, session_id: str) -> Session | None:
        """加载 Session"""
        path = self.storage_dir / f"{session_id}.json"
        if not path.exists():
            return None

        with open(path) as f:
            data = json.load(f)

        return Session(**data)

    def list_sessions(self) -> list[Session]:
        """列出所有 Sessions"""
        sessions = []
        for path in self.storage_dir.glob("*.json"):
            session_id = path.stem
            session = self.load_session(session_id)
            if session:
                sessions.append(session)
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)
```

#### 2.4.3 交互式 UI (ui.py)

```python
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.live import Live
from rich.spinner import Spinner
from agent import Agent, AgentConfig
from agent.types import AgentEvent, AgentEventType
from agent.tools import BashTool, ReadFileTool, WriteFileTool, EditFileTool

class InteractiveUI:
    """交互式终端 UI"""

    def __init__(self, config: CLIConfig):
        self.config = config
        self.console = Console()
        self.agent: Agent | None = None

    async def start(self) -> None:
        """启动交互式会话"""
        self.console.print(Panel.fit(
            "[bold blue]PyAI Agent[/bold blue]\n"
            "Type [green]/help[/green] for commands, [green]/exit[/green] to quit",
            title="Welcome"
        ))

        # 创建 Agent
        agent_config = AgentConfig(
            model=self.config.default_model,
            api_key=self.config.api_key,
            max_turns=self.config.max_turns,
            tools=self._create_tools()
        )

        self.agent = Agent(agent_config)
        self.agent.on_event(self._handle_event)

        # 主循环
        while True:
            try:
                user_input = await self._get_input()

                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                else:
                    await self._process_message(user_input)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /exit to quit[/yellow]")
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")

    async def _get_input(self) -> str:
        """获取用户输入"""
        from rich.prompt import Prompt
        return Prompt.ask("\n[green]You[/green]")

    async def _handle_command(self, command: str) -> None:
        """处理斜杠命令"""
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "/exit":
            raise SystemExit(0)
        elif cmd == "/help":
            self._show_help()
        elif cmd == "/clear":
            self.console.clear()
        elif cmd == "/tools":
            self._list_tools()
        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")

    async def _process_message(self, message: str) -> None:
        """处理用户消息"""
        with Live(Spinner("dots", text="Thinking..."), refresh_per_second=10) as live:
            response_text = ""

            def event_handler(event: AgentEvent) -> None:
                nonlocal response_text

                if event.type == AgentEventType.MESSAGE_UPDATE:
                    # 更新响应文本
                    pass
                elif event.type == AgentEventType.TOOL_EXECUTION_START:
                    tool_name = event.data["tool_name"]
                    live.update(f"[yellow]Using tool: {tool_name}...[/yellow]")
                elif event.type == AgentEventType.TOOL_EXECUTION_END:
                    live.update(Spinner("dots", text="Thinking..."))

            # 临时订阅事件
            self.agent.on_event(event_handler)

            try:
                await self.agent.prompt(message)
            finally:
                # 显示最终响应
                messages = self.agent.messages
                if messages and messages[-1].role == "assistant":
                    content = messages[-1].content[0]["text"]
                    self.console.print(Panel(content, title="[blue]Assistant[/blue]"))

    def _create_tools(self) -> list:
        """创建工具列表"""
        tools = []

        if self.config.enable_bash:
            tools.append(BashTool())

        if self.config.enable_file_tools:
            tools.extend([
                ReadFileTool(),
                WriteFileTool(),
                EditFileTool()
            ])

        return tools

    def _show_help(self) -> None:
        """显示帮助信息"""
        help_text = """
[bold]Available Commands:[/bold]
  /exit      - Exit the application
  /clear     - Clear the screen
  /tools     - List available tools
  /help      - Show this help message
        """
        self.console.print(help_text)

    def _list_tools(self) -> None:
        """列出可用工具"""
        if not self.agent:
            return

        tools = self.agent.config.tools
        if not tools:
            self.console.print("[yellow]No tools available[/yellow]")
            return

        self.console.print("[bold]Available Tools:[/bold]")
        for tool in tools:
            self.console.print(f"  • {tool.definition.name}: {tool.definition.description}")
```

#### 2.4.4 主入口 (main.py)

```python
import asyncio
import argparse
from pathlib import Path
from .config import CLIConfig
from .ui import InteractiveUI

async def main():
    parser = argparse.ArgumentParser(description="PyAI Agent CLI")
    parser.add_argument("--config", "-c", type=Path, help="Config file path")
    parser.add_argument("--model", "-m", default="claude-sonnet-4", help="Model to use")
    parser.add_argument("--api-key", help="API key")
    parser.add_argument("command", nargs="?", help="Single command to execute")

    args = parser.parse_args()

    # 加载配置
    config = CLIConfig.load(args.config)

    # 命令行参数覆盖配置
    if args.model:
        config.default_model = args.model
    if args.api_key:
        config.api_key = args.api_key

    # 启动 UI
    ui = InteractiveUI(config)

    if args.command:
        # 单命令模式
        await ui._process_message(args.command)
    else:
        # 交互式模式
        await ui.start()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 技术实现细节

### 3.1 依赖管理

**packages/ai/pyproject.toml**:
```toml
[project]
name = "pyai"
version = "0.1.0"
dependencies = [
    "anthropic>=0.49.0",
    "pydantic>=2.0",
    "aiofiles>=24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.9.0",
    "pyright>=1.1.350",
]

[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "strict"
```

**packages/agent/pyproject.toml**:
```toml
[project]
name = "pyagent"
version = "0.1.0"
dependencies = [
    "pyai",
]

[tool.uv.sources]
pyai = { workspace = true }
```

**packages/cli/pyproject.toml**:
```toml
[project]
name = "pyai-cli"
version = "0.1.0"
dependencies = [
    "pyagent",
    "rich>=13.0",
    "tomli>=2.0; python_version<'3.11'",
    "tomli-w>=1.0",
]

[tool.uv.sources]
pyagent = { workspace = true }

[project.scripts]
pyai = "cli.main:main"
```

### 3.2 类型检查配置

**严格类型要求**:
- 所有函数参数必须标注类型
- 所有类属性必须标注类型（包括私有属性）
- 重写方法必须使用 `@override` 装饰器
- 不允许有 `Unknown` 类型
- 启用 `strictParameterUnknownValue` 和 `strictListInference`

### 3.3 测试策略

```
packages/ai/tests/
├── conftest.py
├── test_types.py
├── test_registry.py
└── providers/
    └── test_anthropic.py

packages/agent/tests/
├── conftest.py
├── test_agent.py
├── test_loop.py
└── tools/
    ├── test_bash.py
    ├── test_read.py
    └── test_write.py
```

---

## 实现优先级

### Phase 1: AI 核心层（1-2 天）
1. ✅ 创建项目结构和 pyproject.toml
2. ✅ 实现核心类型（types.py）
3. ✅ 实现 Provider 注册表（registry.py）
4. ✅ 实现 Anthropic Provider
5. ✅ 编写单元测试

### Phase 2: Agent 运行时（2-3 天）
1. 实现 Agent 类型定义
2. 实现 Agent 主类
3. 实现 Agent 循环
4. 实现工具基类和接口
5. 实现内置工具（Bash, Read, Write, Edit）
6. 编写单元测试

### Phase 3: CLI 应用（1-2 天）
1. 实现配置管理
2. 实现 Session 管理
3. 实现交互式 UI
4. 实现主入口
5. 集成测试

### Phase 4: 优化和文档（1 天）
1. 完善错误处理
2. 添加日志
3. 编写使用文档
4. 性能优化

---

## 关键设计决策

### 1. 为什么选择 Protocol 而不是 ABC?
- Provider 和 Tool 使用 Protocol（结构子类型）
- 允许第三方实现无需继承特定基类
- 更好的类型推断和编辑器支持

### 2. 为什么使用 Pydantic?
- 强大的类型验证和序列化
- 与 Python 类型系统良好集成
- 支持复杂的嵌套模型

### 3. 为什么使用 AsyncIO?
- 所有 I/O 操作都是异步的
- 支持并发工具执行
- 更好的性能和响应性

### 4. 错误处理策略
- 工具执行错误 → 返回 ToolResultMessage(is_error=True)
- LLM 调用错误 → 抛出异常，由 Agent 捕获并记录
- 配置错误 → 启动时验证，提前失败

---

## 关键实现细节补充

### 5.1 事件流协议详细设计

```python
# packages/ai/src/ai/stream.py
from typing import AsyncIterator, Literal
from dataclasses import dataclass
from .types import AssistantMessage, ToolCall

@dataclass
class StreamTextDelta:
    """文本增量事件"""
    type: Literal["text_delta"] = "text_delta"
    delta: str = ""

@dataclass
class StreamThinkingDelta:
    """思考过程增量（Anthropic 特有）"""
    type: Literal["thinking_delta"] = "thinking_delta"
    delta: str = ""

@dataclass
class StreamToolCallStart:
    """工具调用开始"""
    type: Literal["tool_call_start"] = "tool_call_start"
    tool_call: ToolCall

@dataclass
class StreamToolCallDelta:
    """工具调用参数增量（流式 JSON）"""
    type: Literal["tool_call_delta"] = "tool_call_delta"
    tool_call_id: str
    delta: str

@dataclass
class StreamComplete:
    """流式响应完成"""
    type: Literal["complete"] = "complete"
    message: AssistantMessage

@dataclass
class StreamError:
    """流式响应错误"""
    type: Literal["error"] = "error"
    error: str
    code: str | None = None

StreamEvent = (
    StreamTextDelta |
    StreamThinkingDelta |
    StreamToolCallStart |
    StreamToolCallDelta |
    StreamComplete |
    StreamError
)

class EventStream:
    """事件流基类 - 提供统一的事件转换接口"""

    def __init__(self, raw_stream: AsyncIterator[any]):
        self._raw_stream = raw_stream
        self._buffer = ""

    async def __aiter__(self) -> AsyncIterator[StreamEvent]:
        """异步迭代器接口"""
        async for event in self._convert_stream():
            yield event

    async def _convert_stream(self) -> AsyncIterator[StreamEvent]:
        """子类实现具体的转换逻辑"""
        raise NotImplementedError
```

### 5.2 上下文管理与 Token 计算

```python
# packages/ai/src/ai/context.py
from typing import Sequence
import tiktoken

class ContextManager:
    """上下文管理器 - 处理上下文窗口和 Token 计算"""

    def __init__(self, model: Model, max_tokens: int | None = None):
        self.model = model
        self.max_tokens = max_tokens or model.context_window
        self._encoding = tiktoken.encoding_for_model(model.id)

    def count_tokens(self, text: str) -> int:
        """计算文本的 Token 数量"""
        return len(self._encoding.encode(text))

    def count_message_tokens(self, message: Message) -> int:
        """计算消息的 Token 数量"""
        if isinstance(message, UserMessage):
            text = "".join(c["text"] for c in message.content if c["type"] == "text")
        elif isinstance(message, AssistantMessage):
            text = "".join(c["text"] for c in message.content)
            if message.tool_calls:
                for tc in message.tool_calls:
                    text += tc.name + str(tc.arguments)
        else:
            text = message.content

        return self.count_tokens(text)

    def prune_context(
        self,
        messages: Sequence[Message],
        reserve_tokens: int = 1000
    ) -> list[Message]:
        """剪枝上下文以适应 Token 限制"""
        total_tokens = 0
        pruned = []

        # 从最新的消息开始，保留尽可能多的历史
        for msg in reversed(messages):
            msg_tokens = self.count_message_tokens(msg)
            if total_tokens + msg_tokens > self.max_tokens - reserve_tokens:
                break
            pruned.append(msg)
            total_tokens += msg_tokens

        return list(reversed(pruned))
```

### 5.3 工具执行安全沙箱

```python
# packages/agent/src/agent/tools/security.py
from pathlib import Path
from typing import Callable
import fnmatch

class ToolSecurityPolicy:
    """工具安全策略 - 控制文件系统访问权限"""

    def __init__(
        self,
        allowed_paths: list[str] | None = None,
        blocked_patterns: list[str] | None = None,
        allow_shell: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
    ):
        self.allowed_paths = [Path(p).resolve() for p in (allowed_paths or ["."])]
        self.blocked_patterns = blocked_patterns or [
            "*.pem", "*.key", "*.env", ".env*",
            "**/secrets/**", "**/credentials/**"
        ]
        self.allow_shell = allow_shell
        self.max_file_size = max_file_size

    def is_path_allowed(self, path: str | Path) -> bool:
        """检查路径是否允许访问"""
        target = Path(path).resolve()

        # 检查是否在允许的目录下
        if not any(
            target == allowed or target.is_relative_to(allowed)
            for allowed in self.allowed_paths
        ):
            return False

        # 检查是否匹配禁止模式
        for pattern in self.blocked_patterns:
            if fnmatch.fnmatch(str(target), pattern):
                return False

        return True

    def validate_file_size(self, size: int) -> bool:
        """验证文件大小"""
        return size <= self.max_file_size

    def check_shell_command(self, command: str) -> tuple[bool, str]:
        """检查 Shell 命令是否安全"""
        if not self.allow_shell:
            return False, "Shell commands are disabled"

        # 禁止的危险命令列表
        dangerous_commands = [
            "rm -rf /", "mkfs.", "dd if=/dev/zero",
            ":(){ :|:& };:", "> /dev/sda"
        ]

        for dangerous in dangerous_commands:
            if dangerous in command:
                return False, f"Dangerous command detected: {dangerous}"

        return True, ""

# 全局安全策略实例
default_security_policy = ToolSecurityPolicy()
```

### 5.4 Agent 状态机

```python
# packages/agent/src/agent/state.py
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import AgentEvent

class AgentState(Enum):
    """Agent 状态枚举"""
    IDLE = auto()           # 空闲状态
    THINKING = auto()       # LLM 思考中
    TOOL_EXECUTING = auto() # 工具执行中
    ERROR = auto()          # 错误状态
    STOPPED = auto()        # 已停止

@dataclass
class AgentStateMachine:
    """Agent 状态机 - 管理状态和转换"""
    current: AgentState = AgentState.IDLE
    _history: list[tuple[AgentState, float]] = field(default_factory=list)

    def transition(self, new_state: AgentState) -> bool:
        """尝试状态转换"""
        # 定义有效的状态转换
        valid_transitions = {
            AgentState.IDLE: [AgentState.THINKING, AgentState.STOPPED],
            AgentState.THINKING: [AgentState.TOOL_EXECUTING, AgentState.IDLE, AgentState.ERROR],
            AgentState.TOOL_EXECUTING: [AgentState.THINKING, AgentState.IDLE, AgentState.ERROR],
            AgentState.ERROR: [AgentState.IDLE, AgentState.STOPPED],
            AgentState.STOPPED: [AgentState.IDLE],
        }

        if new_state in valid_transitions.get(self.current, []):
            from time import time
            self._history.append((self.current, time()))
            self.current = new_state
            return True

        return False

    @property
    def can_prompt(self) -> bool:
        """检查是否可以接受新提示"""
        return self.current in [AgentState.IDLE, AgentState.ERROR]

    @property
    def is_running(self) -> bool:
        """检查 Agent 是否正在运行"""
        return self.current in [AgentState.THINKING, AgentState.TOOL_EXECUTING]
```

### 5.5 并发控制与背压

```python
# packages/agent/src/agent/concurrency.py
import asyncio
from typing import TypeVar, ParamSpec
from functools import wraps

T = TypeVar('T')
P = ParamSpec('P')

class ConcurrencyLimiter:
    """并发限制器 - 控制同时执行的工具数量"""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_tasks: set[asyncio.Task] = set()

    async def execute(self, coro: Awaitable[T]) -> T:
        """在并发限制下执行协程"""
        async with self._semaphore:
            task = asyncio.create_task(coro)
            self._active_tasks.add(task)
            try:
                return await task
            finally:
                self._active_tasks.discard(task)

    async def cancel_all(self) -> None:
        """取消所有活动任务"""
        for task in list(self._active_tasks):
            task.cancel()
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        self._active_tasks.clear()

    @property
    def active_count(self) -> int:
        """当前活动任务数"""
        return len(self._active_tasks)

def rate_limit(calls: int, period: float):
    """速率限制装饰器"""
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        timestamps: list[float] = []
        lock = asyncio.Lock()

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async with lock:
                now = asyncio.get_event_loop().time()
                # 清理过期的时间戳
                timestamps[:] = [t for t in timestamps if now - t < period]

                if len(timestamps) >= calls:
                    sleep_time = timestamps[0] + period - now
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)

                timestamps.append(now)

            return await func(*args, **kwargs)

        return wrapper
    return decorator
```

---

## 验证计划

### 1. 类型检查
```bash
cd packages/ai && uv run pyright
```

### 2. 代码风格
```bash
cd packages/ai && uv run ruff check .
```

### 3. 单元测试
```bash
cd packages/ai && uv run pytest
```

### 4. 集成测试
```bash
cd packages/cli && uv run pyai "Hello, what can you do?"
```

---

## 参考资源

- **pi-mono**: `refer/pi-mono/packages/ai`, `refer/pi-mono/packages/agent`
- **kimi-cli**: `refer/kimi-cli/packages/kosong`, `refer/kimi-cli/src/kimi_cli`
- **文档**:
  - Anthropic API: https://docs.anthropic.com/
  - Pydantic: https://docs.pydantic.dev/
  - Python Protocol: https://docs.python.org/3/library/typing.html#typing.Protocol

---

## 项目初始化与开发工作流

### 6.1 项目初始化脚本

```bash
#!/bin/bash
# scripts/init-project.sh

echo "🚀 Initializing PyAI Project..."

# 安装 Python 3.14
echo "📦 Installing Python 3.14..."
uv python install 3.14

# 创建虚拟环境
echo "🌍 Creating virtual environment..."
uv venv --python 3.14

# 同步所有包依赖
echo "⬇️ Syncing dependencies..."
uv sync --all-packages

# 安装开发工具
echo "🛠️ Installing development tools..."
uv pip install ruff pyright pytest pytest-asyncio

# 创建配置文件目录
mkdir -p ~/.config/pyai/sessions

# 创建默认配置（如果不存在）
if [ ! -f ~/.config/pyai/config.toml ]; then
    echo "⚙️ Creating default configuration..."
    cat > ~/.config/pyai/config.toml << 'EOF'
default_model = "claude-sonnet-4"
max_turns = 50
enable_bash = true
enable_file_tools = true
enable_search_tools = true
EOF
fi

echo "✅ Project initialized successfully!"
echo ""
echo "Next steps:"
echo "1. Set your ANTHROPIC_API_KEY environment variable"
echo "2. Run: uv run pyai --help"
echo "3. Run: uv run pyai"
```

### 6.2 Git 工作流配置

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13", "3.14"]

    steps:
    - uses: actions/checkout@v4

    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        version: "0.5.x"

    - name: Setup Python
      run: uv python install ${{ matrix.python-version }}

    - name: Sync dependencies
      run: uv sync --all-packages

    - name: Lint
      run: uv run ruff check packages/

    - name: Type check
      run: |
        cd packages/ai && uv run pyright
        cd ../agent && uv run pyright
        cd ../cli && uv run pyright

    - name: Test
      run: |
        cd packages/ai && uv run pytest
        cd ../agent && uv run pytest
```

### 6.3 Makefile 快捷命令

```makefile
.PHONY: all init install lint typecheck test check clean

# 默认目标
all: check

# 初始化项目
init:
	bash scripts/init-project.sh

# 安装依赖
install:
	uv sync --all-packages

# 代码检查
lint:
	uv run ruff check packages/
	uv run ruff format --check packages/

# 格式化代码
format:
	uv run ruff format packages/
	uv run ruff check --fix packages/

# 类型检查
typecheck:
	@echo "Checking packages/ai..."
	@cd packages/ai && uv run pyright
	@echo "Checking packages/agent..."
	@cd packages/agent && uv run pyright
	@echo "Checking packages/cli..."
	@cd packages/cli && uv run pyright

# 运行测试
test:
	@cd packages/ai && uv run pytest -v
	@cd packages/agent && uv run pytest -v

# 完整检查（提交前必做）
check: lint typecheck test

# 清理缓存
clean:
	rm -rf .venv
	rm -rf .ruff_cache
	rm -rf packages/*/.pytest_cache
	rm -rf packages/*/__pycache__
	rm -rf packages/*/*/__pycache__
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# 交互式运行
dev:
	uv run pyai

# 单次命令
run:
	uv run pyai "$(cmd)"
```

### 6.4 开发环境配置

```json
// .vscode/settings.json
{
  "python.analysis.typeCheckingMode": "strict",
  "python.analysis.autoImportCompletions": true,
  "python.analysis.inlayHints.functionReturnTypes": true,
  "python.analysis.inlayHints.variableTypes": true,
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll": "explicit",
    "source.organizeImports": "explicit"
  },
  "ruff.organizeImports": true,
  "ruff.fixAll": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["packages"],
  "files.watcherExclude": {
    "**/.venv/**": true,
    "**/__pycache__/**": true,
    "**/.ruff_cache/**": true
  }
}
```

```toml
# .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "tamasfe.even-better-toml",
    "github.vscode-github-actions"
  ]
}
```

---

## 实施检查清单

### Phase 1: AI 核心层
- [ ] 创建 `packages/ai/` 结构和 `pyproject.toml`
- [ ] 实现 `types.py` - 核心消息和工具类型
- [ ] 实现 `registry.py` - Provider 注册表
- [ ] 实现 `stream.py` - 事件流协议
- [ ] 实现 `context.py` - 上下文管理
- [ ] 实现 `providers/anthropic.py` - Anthropic Provider
- [ ] 编写单元测试
- [ ] **类型检查**: `cd packages/ai && uv run pyright` (必须 0 错误)

### Phase 2: Agent 运行时
- [ ] 创建 `packages/agent/` 结构和 `pyproject.toml`
- [ ] 实现 `types.py` - Agent 类型和事件
- [ ] 实现 `state.py` - 状态机管理
- [ ] 实现 `agent.py` - Agent 主类
- [ ] 实现 `loop.py` - 执行循环
- [ ] 实现 `concurrency.py` - 并发控制
- [ ] 实现工具基类和基础工具（Bash, Read, Write, Edit）
- [ ] 实现 `tools/security.py` - 安全策略
- [ ] 编写单元测试
- [ ] **类型检查**: `cd packages/agent && uv run pyright` (必须 0 错误)

### Phase 3: CLI 应用
- [ ] 创建 `packages/cli/` 结构和 `pyproject.toml`
- [ ] 实现 `config.py` - 配置管理
- [ ] 实现 `session.py` - Session 管理
- [ ] 实现 `ui.py` - Rich 交互式 UI
- [ ] 实现 `main.py` - 主入口
- [ ] 创建启动脚本 `scripts/init-project.sh`
- [ ] 配置 GitHub Actions CI
- [ ] 创建 Makefile
- [ ] 编写集成测试
- [ ] **类型检查**: `cd packages/cli && uv run pyright` (必须 0 错误)

### Phase 4: 文档与发布
- [ ] 编写根目录 `README.md`
- [ ] 为每个包编写 `README.md`
- [ ] 编写 `CLAUDE.md` 项目记忆
- [ ] 添加使用示例
- [ ] 完善错误消息和用户引导
- [ ] **完整检查**: `make check` (全部通过)

### 质量门禁
- [ ] **Python 版本**: 3.12+ (推荐 3.14)
- [ ] **类型检查**: Pyright Strict Mode 0 错误
- [ ] **代码风格**: Ruff 0 错误
- [ ] **测试覆盖**: 核心代码 > 80%
- [ ] **文档**: 所有公共 API 有 docstring
- [ ] **安全**: 工具沙箱策略已实施

---

## 预期成果

### 交付物
1. **可运行的 CLI 工具**: `pyai` 命令
2. **完整的包结构**: ai → agent → cli 三层架构
3. **基础工具集**: Bash, Read, Write, Edit 等核心工具
4. **交互式体验**: Rich 驱动的实时流式 UI
5. **会话管理**: 持久化的对话历史
6. **类型安全**: 全代码库 Pyright Strict 0 错误
7. **测试覆盖**: 单元测试 + 集成测试
8. **开发工具**: Makefile, CI/CD, VSCode 配置

### 功能演示

```bash
# 交互式模式
$ uv run pyai
PyAI Agent
Type /help for commands, /exit to quit

You: 查看当前目录的文件
Assistant: I'll list the files in the current directory for you.

[bash] $ ls -la
.total 32
drwxr-xr-x  8 user staff  256 Mar 17 14:32 .
drwxr-xr-x  5 user staff  160 Mar 17 12:00 ..
-rw-r--r--  1 user staff  540 Mar 17 12:43 pyproject.toml
...

The current directory contains:
- pyproject.toml: Project configuration
- packages/: Source code packages
- README.md: Project readme

# 单命令模式
$ uv run pyai "创建一个新的 Python 文件 hello.py，内容为打印 Hello World"
Assistant: I'll create a new Python file for you.

[write_file] Creating hello.py
Content:
print("Hello World")

File created successfully at: hello.py

# Session 管理
$ uv run pyai --list-sessions
Recent sessions:
1. session-abc123 - 2024-03-17 14:30
2. session-def456 - 2024-03-17 13:15

$ uv run pyai --resume session-abc123
Resuming session from 2024-03-17 14:30...
```

### 性能指标
- **启动时间**: < 1s
- **首 Token 延迟**: < 500ms (网络正常)
- **流式响应**: 实时显示，无卡顿
- **并发工具**: 支持 5+ 工具并行执行
- **上下文管理**: 自动剪枝，支持 200K Token

这个方案完整吗？有什么需要调整的地方吗？
