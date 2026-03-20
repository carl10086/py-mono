# Coding Agent 数据模型

> 核心数据结构、类型定义和状态流转

---

## 1. 会话数据模型

### 1.1 核心类型层次

```
SessionEntry (基类)
├── SessionHeader
├── SessionMessageEntry
├── ThinkingLevelChangeEntry
├── ModelChangeEntry
├── CompactionEntry
├── BranchSummaryEntry
├── CustomEntry
├── CustomMessageEntry
└── LabelEntry
```

### 1.2 基类定义

```typescript
interface SessionEntry {
  id: string;           // 唯一标识符 (UUID)
  type: EntryType;      // 条目类型
  parentId: string;     // 父节点 ID（树形结构）
  timestamp: number;    // Unix 时间戳（毫秒）
}

type EntryType = 
  | 'header'
  | 'message' 
  | 'thinkingLevelChange'
  | 'modelChange'
  | 'compaction'
  | 'branchSummary'
  | 'custom'
  | 'customMessage'
  | 'label';
```

### 1.3 各类型详细定义

#### SessionHeader - 会话头

```typescript
interface SessionHeader extends SessionEntry {
  type: 'header';
  sessionId: string;        // 会话唯一 ID
  cwd: string;              // 工作目录
  createdAt: number;        // 创建时间
  version: string;          // 数据格式版本
}

// 示例
{
  "id": "root",
  "type": "header",
  "parentId": "",
  "timestamp": 1704067200000,
  "sessionId": "sess-abc123",
  "cwd": "/home/user/project",
  "createdAt": 1704067200000,
  "version": "1.0.0"
}
```

#### SessionMessageEntry - 消息条目

```typescript
interface SessionMessageEntry extends SessionEntry {
  type: 'message';
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: ContentBlock[];  // 消息内容块
  name?: string;            // 可选：工具名称或角色名
  toolCalls?: ToolCall[];   // assistant 的 tool 调用
  toolCallId?: string;      // tool 消息的调用 ID
}

type ContentBlock = 
  | TextBlock 
  | ThinkingBlock 
  | ToolCallBlock 
  | ToolResultBlock
  | ImageBlock;

interface TextBlock {
  type: 'text';
  text: string;
}

interface ThinkingBlock {
  type: 'thinking';
  thinking: string;
  signature?: string;  // 可选：思考签名（某些模型）
}

interface ToolCallBlock {
  type: 'toolCall';
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}

interface ToolResultBlock {
  type: 'toolResult';
  toolCallId: string;
  content: ContentBlock[];
  isError: boolean;
}

interface ImageBlock {
  type: 'image';
  source: {
    type: 'base64' | 'url';
    mediaType: string;
    data: string;
  };
}

// 示例：用户消息
{
  "id": "msg-1",
  "type": "message",
  "parentId": "root",
  "timestamp": 1704067201000,
  "role": "user",
  "content": [{ "type": "text", "text": "Hello!" }]
}

// 示例：助手消息（带 tool 调用）
{
  "id": "msg-2",
  "type": "message",
  "parentId": "msg-1",
  "timestamp": 1704067202000,
  "role": "assistant",
  "content": [
    { "type": "text", "text": "I'll help you with that." },
    {
      "type": "toolCall",
      "id": "call-1",
      "name": "read",
      "arguments": { "filePath": "/path/to/file" }
    }
  ],
  "toolCalls": [{
    "id": "call-1",
    "name": "read",
    "arguments": { "filePath": "/path/to/file" }
  }]
}

// 示例：工具结果消息
{
  "id": "msg-3",
  "type": "message",
  "parentId": "msg-2",
  "timestamp": 1704067203000,
  "role": "tool",
  "toolCallId": "call-1",
  "content": [
    { "type": "text", "text": "File content..." }
  ]
}
```

#### ThinkingLevelChangeEntry - 思考等级变更

```typescript
interface ThinkingLevelChangeEntry extends SessionEntry {
  type: 'thinkingLevelChange';
  level: number;            // 思考等级（0-3）
  previousLevel: number;    // 之前的等级
  reason?: string;          // 变更原因（可选）
}

// 示例
{
  "id": "tl-1",
  "type": "thinkingLevelChange",
  "parentId": "msg-2",
  "timestamp": 1704067202500,
  "level": 2,
  "previousLevel": 0,
  "reason": "User requested more detailed reasoning"
}
```

#### ModelChangeEntry - 模型变更

```typescript
interface ModelChangeEntry extends SessionEntry {
  type: 'modelChange';
  modelId: string;          // 新模型 ID
  previousModelId: string;  // 之前的模型 ID
  provider: string;         // Provider 名称
}

// 示例
{
  "id": "mc-1",
  "type": "modelChange",
  "parentId": "msg-5",
  "timestamp": 1704067210000,
  "modelId": "claude-3-sonnet-20240229",
  "previousModelId": "claude-3-haiku-20240307",
  "provider": "anthropic"
}
```

#### CompactionEntry - 压缩条目

```typescript
interface CompactionEntry extends SessionEntry {
  type: 'compaction';
  summary: string;          // Markdown 格式摘要
  compressedCount: number;  // 压缩的消息数量
  originalTokenCount: number;   // 原始 Token 数量
  summaryTokenCount: number;    // 摘要 Token 数量
  compressedMessageIds: string[];   // 被压缩的消息 ID 列表
  cutoffIndex: number;      // 截断点索引
}

// 示例
{
  "id": "compact-1",
  "type": "compaction",
  "parentId": "msg-20",
  "timestamp": 1704067250000,
  "summary": "## Goal\nBuild a user authentication system...\n\n## Progress\n### Done\n- [x] Database schema\n- [x] User model\n\n### In Progress\n- [ ] Login endpoint",
  "compressedCount": 15,
  "originalTokenCount": 3500,
  "summaryTokenCount": 250,
  "compressedMessageIds": ["msg-5", "msg-6", ..., "msg-19"],
  "cutoffIndex": 5
}
```

#### BranchSummaryEntry - 分支摘要

```typescript
interface BranchSummaryEntry extends SessionEntry {
  type: 'branchSummary';
  sourceSessionId: string;      // 源会话 ID
  branchedAtEntryId: string;    // 分支点条目 ID
  summary: string;              // 分支前上下文摘要
}

// 示例
{
  "id": "branch-1",
  "type": "branchSummary",
  "parentId": "root",
  "timestamp": 1704067300000,
  "sourceSessionId": "sess-original",
  "branchedAtEntryId": "msg-10",
  "summary": "Previous conversation was about implementing a REST API..."
}
```

#### CustomEntry - 扩展私有数据

```typescript
interface CustomEntry extends SessionEntry {
  type: 'custom';
  extensionId: string;      // 扩展标识
  data: unknown;            // 扩展自定义数据
}

// 示例
{
  "id": "custom-1",
  "type": "custom",
  "parentId": "msg-8",
  "timestamp": 1704067220000,
  "extensionId": "my-extension",
  "data": {
    "key": "value",
    "count": 42
  }
}
```

#### CustomMessageEntry - 扩展消息

```typescript
interface CustomMessageEntry extends SessionEntry {
  type: 'customMessage';
  extensionId: string;
  role: 'user' | 'assistant' | 'system';
  content: ContentBlock[];
}

// 示例
{
  "id": "cm-1",
  "type": "customMessage",
  "parentId": "msg-8",
  "timestamp": 1704067221000,
  "extensionId": "code-review-extension",
  "role": "assistant",
  "content": [
    { "type": "text", "text": "Code review completed. 3 issues found." }
  ]
}
```

#### LabelEntry - 用户书签

```typescript
interface LabelEntry extends SessionEntry {
  type: 'label';
  name: string;             // 标签名称
  color?: string;           // 颜色（可选）
  note?: string;            // 备注（可选）
}

// 示例
{
  "id": "label-1",
  "type": "label",
  "parentId": "msg-15",
  "timestamp": 1704067230000,
  "name": "Important decision",
  "color": "#ff0000",
  "note": "We decided to use PostgreSQL instead of MySQL"
}
```

---

## 2. Agent 数据模型

### 2.1 AgentContext - 运行时上下文

```typescript
interface AgentContext {
  systemPrompt: string;           // 系统提示词
  messages: Message[];            // 完整对话历史
  tools: AgentTool[];             // 可用工具列表
  metadata?: Record<string, unknown>;  // 元数据（扩展使用）
}

interface Message {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: ContentBlock[];
  name?: string;
  toolCalls?: ToolCall[];
  toolCallId?: string;
}
```

### 2.2 AgentConfig - 循环配置

```typescript
interface AgentConfig {
  // LLM 配置
  model: ModelConfig;
  
  // 流式调用函数
  streamFn: StreamFunction;
  
  // 工具执行模式
  toolExecution: 'sequential' | 'parallel';
  
  // 消息获取回调
  getSteeringMessages?: () => Promise<Message[]>;
  getFollowUpMessages?: () => Promise<Message[]>;
  
  // Tool Hook
  beforeToolCall?: BeforeToolCallHook;
  afterToolCall?: AfterToolCallHook;
  
  // 其他配置
  maxIterations?: number;         // 最大迭代次数
  timeout?: number;               // 超时时间（毫秒）
  signal?: AbortSignal;           // 取消信号
}

interface ModelConfig {
  provider: string;
  modelId: string;
  temperature?: number;
  maxTokens?: number;
  thinkingLevel?: number;
}

type StreamFunction = (
  messages: Message[],
  tools: AgentTool[],
  config: ModelConfig
) => Promise<LlmStream>;

type BeforeToolCallHook = (
  toolCall: ToolCall,
  context: AgentContext
) => Promise<BeforeToolCallResult>;

interface BeforeToolCallResult {
  block?: boolean;        // 是否阻止执行
  blockReason?: string;   // 阻止原因
  modifiedArgs?: Record<string, unknown>;  // 修改后的参数
}

type AfterToolCallHook = (
  toolCall: ToolCall,
  result: ToolResult,
  context: AgentContext
) => Promise<AfterToolCallResult>;

interface AfterToolCallResult {
  modifiedResult?: ToolResult;  // 修改后的结果
}
```

### 2.3 AgentEvent - 事件类型

```typescript
type AgentEvent =
  | AgentStartEvent
  | AgentEndEvent
  | TurnStartEvent
  | TurnEndEvent
  | MessageStartEvent
  | MessageUpdateEvent
  | MessageEndEvent
  | ToolExecutionStartEvent
  | ToolExecutionUpdateEvent
  | ToolExecutionEndEvent;

interface AgentStartEvent {
  type: 'agent_start';
  timestamp: number;
  context: AgentContext;
}

interface AgentEndEvent {
  type: 'agent_end';
  timestamp: number;
  context: AgentContext;
  newMessages: Message[];
}

interface TurnStartEvent {
  type: 'turn_start';
  timestamp: number;
  turnNumber: number;
}

interface TurnEndEvent {
  type: 'turn_end';
  timestamp: number;
  turnNumber: number;
  message: AssistantMessage;
  toolResults: ToolResultMessage[];
}

interface MessageStartEvent {
  type: 'message_start';
  timestamp: number;
  message: Message;
}

interface MessageUpdateEvent {
  type: 'message_update';
  timestamp: number;
  message: AssistantMessage;
  delta: ContentBlock;
}

interface MessageEndEvent {
  type: 'message_end';
  timestamp: number;
  message: Message;
}

interface ToolExecutionStartEvent {
  type: 'tool_execution_start';
  timestamp: number;
  toolCallId: string;
  toolName: string;
  arguments: Record<string, unknown>;
}

interface ToolExecutionUpdateEvent {
  type: 'tool_execution_update';
  timestamp: number;
  toolCallId: string;
  update: ToolExecutionUpdate;
}

interface ToolExecutionEndEvent {
  type: 'tool_execution_end';
  timestamp: number;
  toolCallId: string;
  toolName: string;
  result: ToolResult;
  duration: number;
}
```

### 2.4 Tool 定义

```typescript
interface AgentTool<TParameters extends TSchema = TSchema, TDetails = unknown> {
  name: string;                     // 工具名称
  label: string;                    // 显示标签
  description: string;              // 功能描述
  parameters: TParameters;          // 参数模式（TypeBox schema）
  
  execute: (
    toolCallId: string,
    params: Static<TParameters>,
    signal?: AbortSignal,
    onUpdate?: AgentToolUpdateCallback<TDetails>,
    context?: ToolExecutionContext
  ) => Promise<AgentToolResult<TDetails>>;
}

type AgentToolUpdateCallback<TDetails> = (
  update: AgentToolUpdate<TDetails>
) => void;

interface AgentToolUpdate<TDetails> {
  type: 'output' | 'progress' | 'status';
  data: TDetails;
  timestamp: number;
}

interface AgentToolResult<TDetails> {
  content: ContentBlock[];      // 结果内容
  details?: TDetails;           // 详细数据（扩展使用）
  isError?: boolean;            // 是否错误
}

interface ToolExecutionContext {
  cwd: string;                  // 当前工作目录
  sessionId: string;            // 会话 ID
  extensionStorage?: unknown;   // 扩展存储（扩展工具使用）
}
```

---

## 3. 模型相关数据模型

### 3.1 ModelDefinition - 模型定义

```typescript
interface ModelDefinition {
  id: string;                   // 模型唯一 ID
  name: string;                 // 显示名称
  provider: string;             // Provider ID
  
  // 能力
  capabilities: ModelCapabilities;
  
  // 限制
  contextWindow: number;        // 上下文窗口大小
  maxOutputTokens?: number;     // 最大输出 Token
  
  // 成本（可选）
  costPerInputToken?: number;   // 输入 Token 成本
  costPerOutputToken?: number;  // 输出 Token 成本
}

interface ModelCapabilities {
  supportsStreaming: boolean;       // 支持流式
  supportsToolCalling: boolean;     // 支持 Tool 调用
  supportsVision: boolean;          // 支持图像输入
  supportsThinking: boolean;        // 支持思考模式
  supportedThinkingLevels?: number[]; // 支持的思考等级
}

// 示例
{
  "id": "claude-3-sonnet-20240229",
  "name": "Claude 3 Sonnet",
  "provider": "anthropic",
  "capabilities": {
    "supportsStreaming": true,
    "supportsToolCalling": true,
    "supportsVision": true,
    "supportsThinking": false
  },
  "contextWindow": 200000,
  "maxOutputTokens": 4096,
  "costPerInputToken": 0.000003,
  "costPerOutputToken": 0.000015
}
```

### 3.2 ProviderDefinition - Provider 定义

```typescript
interface ProviderDefinition {
  id: string;                   // Provider ID
  name: string;                 // 显示名称
  
  // API 配置
  baseUrl?: string;             // 自定义 Base URL
  authType: 'apiKey' | 'oauth' | 'none';
  
  // 默认请求头
  defaultHeaders?: Record<string, string>;
  
  // 支持的模型
  models: ModelDefinition[];
}

// 示例
{
  "id": "anthropic",
  "name": "Anthropic",
  "authType": "apiKey",
  "models": [
    {
      "id": "claude-3-opus-20240229",
      "name": "Claude 3 Opus",
      ...
    },
    {
      "id": "claude-3-sonnet-20240229",
      "name": "Claude 3 Sonnet",
      ...
    }
  ]
}
```

### 3.3 ResolvedModel - 解析后的模型

```typescript
interface ResolvedModel {
  id: string;
  name: string;
  provider: ProviderDefinition;
  
  // 合并后的配置（用户覆盖 + 默认）
  config: ModelConfig;
  
  // 实际使用的端点
  baseUrl: string;
  
  // 认证信息
  apiKey?: string;
}
```

---

## 4. 扩展系统数据模型

### 4.1 Extension 定义

```typescript
interface Extension {
  id: string;                   // 扩展 ID
  name: string;                 // 显示名称
  version: string;              // 版本
  description?: string;         // 描述
  author?: string;              // 作者
  
  // 入口点
  main: string;                 // 主文件路径
  
  // 激活事件
  activationEvents?: string[];  // 何时激活
  
  // 贡献点
  contributes?: ExtensionContributes;
}

interface ExtensionContributes {
  commands?: CommandDefinition[];
  shortcuts?: ShortcutDefinition[];
  flags?: FlagDefinition[];
  themes?: ThemeDefinition[];
  prompts?: PromptTemplate[];
}
```

### 4.2 CommandDefinition - 命令定义

```typescript
interface CommandDefinition {
  name: string;                 // 命令名称（如 "search"）
  label: string;                // 显示标签
  description: string;          // 描述
  
  // 参数定义
  arguments?: CommandArgument[];
  
  // 处理器
  handler: CommandHandler;
}

interface CommandArgument {
  name: string;
  description: string;
  type: 'string' | 'number' | 'boolean';
  required: boolean;
  default?: unknown;
}

type CommandHandler = (
  args: Record<string, unknown>,
  context: CommandContext
) => Promise<CommandResult>;

interface CommandContext {
  session: AgentSession;
  ui: UIAPI;
}

interface CommandResult {
  success: boolean;
  message?: string;
  data?: unknown;
}
```

### 4.3 ExtensionAPI 接口

```typescript
interface ExtensionAPI {
  // 版本
  readonly version: string;
  
  // 事件订阅
  on<T extends AgentEventType>(
    event: T,
    handler: AgentEventHandler<T>
  ): Unsubscribe;
  
  once<T extends AgentEventType>(
    event: T,
    handler: AgentEventHandler<T>
  ): void;
  
  // 工具注册
  registerTool<TParams extends TSchema, TDetails>(
    tool: AgentTool<TParams, TDetails>
  ): Unregister;
  
  // 命令注册
  registerCommand(
    name: string,
    handler: CommandHandler,
    options?: CommandOptions
  ): Unregister;
  
  registerShortcut(
    key: string,
    handler: ShortcutHandler,
    options?: ShortcutOptions
  ): Unregister;
  
  registerFlag(
    name: string,
    options: FlagOptions
  ): void;
  
  // Provider 注册
  registerProvider(provider: ModelProvider): Unregister;
  unregisterProvider(providerId: string): void;
  
  // UI API
  readonly ui: UIAPI;
  
  // 会话控制
  sendMessage(message: Message): Promise<void>;
  sendUserMessage(text: string): Promise<void>;
  appendEntry(entry: CustomEntry): Promise<void>;
  
  // 存储（扩展私有）
  getStorage<T>(): Promise<T>;
  setStorage<T>(data: T): Promise<void>;
}
```

---

## 5. UI 数据模型

### 5.1 UIState - UI 状态

```typescript
interface UIState {
  // 输入状态
  input: {
    text: string;
    isMultiline: boolean;
    cursorPosition: number;
  };
  
  // 消息列表
  messages: UIMessage[];
  
  // 当前状态
  status: 'idle' | 'streaming' | 'executing_tools' | 'waiting';
  
  // 工具执行状态
  activeToolExecutions: ActiveToolExecution[];
  
  // 模型信息
  currentModel: ResolvedModel | null;
  
  // Token 使用
  tokenUsage: TokenUsage;
}

interface UIMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: ContentBlock[];
  status: 'pending' | 'streaming' | 'complete' | 'error';
  timestamp: number;
  
  // 工具相关
  toolCalls?: UIToolCall[];
  toolResults?: UIToolResult[];
}

interface UIToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status: 'pending' | 'executing' | 'complete';
}

interface UIToolResult {
  toolCallId: string;
  content: ContentBlock[];
  isError: boolean;
  executionTime: number;
}

interface TokenUsage {
  input: number;
  output: number;
  total: number;
  limit: number;
}
```

### 5.2 UIAPI - UI 交互接口

```typescript
interface UIAPI {
  // 显示消息
  showMessage(message: string, type?: 'info' | 'warning' | 'error'): void;
  
  // 输入框
  input: {
    getValue(): string;
    setValue(value: string): void;
    focus(): void;
    blur(): void;
  };
  
  // 选择器
  select<T>(
    items: SelectItem<T>[],
    options?: SelectOptions
  ): Promise<T | undefined>;
  
  confirm(message: string): Promise<boolean>;
  
  // 编辑器
  editor: {
    open(filePath: string): Promise<void>;
    setContent(content: string): void;
    getContent(): string;
  };
  
  // 自定义组件
  setWidget(widget: Widget | null): void;
  setFooter(footer: FooterComponent | null): void;
  setHeader(header: HeaderComponent | null): void;
}
```

---

## 6. 配置数据模型

### 6.1 UserSettings - 用户设置

```typescript
interface UserSettings {
  // 模型默认配置
  defaultModel: string;
  defaultThinkingLevel: number;
  
  // 自动压缩配置
  autoCompaction: AutoCompactionSettings;
  
  // 显示配置
  display: DisplaySettings;
  
  // 扩展配置
  extensions: ExtensionSettings;
  
  // 快捷键配置
  keybindings: Record<string, string>;
}

interface AutoCompactionSettings {
  enabled: boolean;
  tokenThreshold: number;       // Token 阈值（默认 80%）
  messageThreshold: number;     // 消息阈值（默认 50）
  minMessagesToCompact: number; // 最少压缩消息数（默认 10）
  preserveRecentMessages: number; // 保留最近消息数（默认 5）
}

interface DisplaySettings {
  theme: string;
  fontSize: number;
  showTimestamps: boolean;
  compactMode: boolean;
}

interface ExtensionSettings {
  enabled: string[];            // 启用的扩展列表
  disabled: string[];           // 禁用的扩展列表
  config: Record<string, unknown>; // 扩展特定配置
}
```

### 6.2 配置文件位置

```
~/.pi/
├── config.json               # 主配置文件
├── agent/
│   ├── models.json           # 自定义模型
│   ├── extensions/           # 扩展目录
│   ├── skills/               # 技能目录
│   ├── prompts/              # 提示词模板
│   └── themes/               # 主题目录
└── sessions/                 # 会话存储
    ├── {sessionId}.jsonl
    └── archive/              # 归档会话
```

---

## 7. 数据流转图

### 7.1 消息生命周期

```
User Input
    │
    ▼
[UserMessage]
    │
    ▼
SessionManager.appendMessage()
    │
    ▼
SessionMessageEntry (持久化到 JSONL)
    │
    ▼
AgentContext.messages (加载到内存)
    │
    ▼
LLM Stream
    │
    ▼
[AssistantMessage]
    │
    ▼
Tool Calls?
    ├── Yes ──▶ Tool Execution ──▶ [ToolResultMessage]
    │                               │
    │                               ▼
    │                           SessionManager.appendMessage()
    │                               │
    │                               ▼
    │                           Back to LLM Stream
    │
    └── No ───▶ SessionManager.appendMessage()
                    │
                    ▼
                Complete
```

### 7.2 压缩生命周期

```
Token Count Check
    │
    ▼
Exceeds Threshold?
    ├── No ──▶ Continue
    │
    └── Yes
        │
        ▼
    Calculate Cutoff
        │
        ▼
    Extract Messages to Summarize
        │
        ▼
    Generate Summary (LLM Call)
        │
        ▼
    Create CompactionEntry
        │
        ▼
    SessionManager.appendCompactionEntry()
        │
        ▼
    Truncate Messages
        │
        ▼
    Build New Context
        │
        ▼
    Continue with Compacted Context
```

---

## 8. Python 类型映射

将 TypeScript 类型映射到 Python：

| TypeScript | Python |
|-----------|--------|
| `interface` | `dataclass` / `TypedDict` |
| `type` | `TypeAlias` |
| `string` | `str` |
| `number` | `int` / `float` |
| `boolean` | `bool` |
| `Array<T>` | `list[T]` |
| `Record<K, V>` | `dict[K, V]` |
| `unknown` | `Any` |
| `undefined` | `None` |
| `T \| U` | `Union[T, U]` 或 `T \| U` (Python 3.10+) |
| `Partial<T>` | 可选字段 |

### 示例映射

```python
from dataclasses import dataclass
from typing import Literal, Any
from datetime import datetime

@dataclass
class SessionEntry:
    id: str
    type: Literal['header', 'message', 'compaction', ...]
    parent_id: str
    timestamp: int  # Unix timestamp in milliseconds

@dataclass
class SessionMessageEntry(SessionEntry):
    role: Literal['user', 'assistant', 'system', 'tool']
    content: list[ContentBlock]
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
```
