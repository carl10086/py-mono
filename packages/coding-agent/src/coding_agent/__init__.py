"""Coding Agent 模块。

提供代码编辑工具集、会话持久化和 AgentSession 核心抽象。
完全对齐 pi-mono 架构实现。
"""

from __future__ import annotations

__version__ = "0.1.0"

# Phase 3: AgentSession 核心
from coding_agent.agent_session import AgentSession, AgentSessionConfig, PromptOptions
from coding_agent.bash_executor import BashResult, execute_bash
from coding_agent.messages import (
    COMPACTION_SUMMARY_PREFIX,
    COMPACTION_SUMMARY_SUFFIX,
    BRANCH_SUMMARY_PREFIX,
    BRANCH_SUMMARY_SUFFIX,
    BashExecutionMessage,
    CustomMessage,
    BranchSummaryMessage,
    CompactionSummaryMessage,
    ExtendedMessage,
    bash_execution_to_text,
    convert_to_llm,
    create_branch_summary_message,
    create_compaction_summary_message,
    create_custom_message,
)
from coding_agent.model_registry import ModelInfo, ModelRegistry
from coding_agent.settings_manager import (
    CompactionSettings,
    RetrySettings,
    Settings,
    SettingsError,
    SettingsManager,
)
from coding_agent.system_prompt import (
    TOOL_DESCRIPTIONS,
    BuildSystemPromptOptions,
    build_system_prompt,
)

# Phase 4: 压缩与上下文管理
from coding_agent.compaction import (
    # Utils
    FileOperations,
    create_file_ops,
    extract_file_ops_from_message,
    compute_file_lists,
    format_file_operations,
    TOOL_RESULT_MAX_CHARS,
    serialize_conversation,
    SUMMARIZATION_SYSTEM_PROMPT,
    # Compaction
    CompactionSettings as CompactionConfigSettings,
    DEFAULT_COMPACTION_SETTINGS,
    calculate_context_tokens,
    estimate_tokens,
    estimate_context_tokens,
    should_compact,
    CompactionDetails,
    CompactionResult,
    PrepareCompactionResult,
    prepare_compaction,
    compact,
    # Branch Summary
    BranchSummaryResult,
    BranchSummaryDetails,
    BranchPreparation,
    CollectEntriesResult,
    collect_entries_for_branch_summary,
    prepare_branch_summary,
    generate_branch_summary,
)

# Phase 5: SDK
from coding_agent.sdk import (
    create_coding_tools,
    create_read_only_tools,
    create_agent_session,
    CreateAgentSessionOptions,
    CreateAgentSessionResult,
)

# Phase 6: 扩展系统
from coding_agent.extensions import (
    Extension,
    ExtensionContext,
    ExtensionRunner,
    ToolDefinition,
    clear_registered_tools,
    discover_extensions,
    get_wrapped_tools,
    load_extension,
    load_extensions,
    register_tool,
    unregister_tool,
    wrap_registered_tool,
    wrap_registered_tools,
)

# Phase 7: 技能系统
from coding_agent.skills import (
    Skill,
    format_skill_for_prompt,
    format_skills_for_prompt,
    get_skill_by_tag,
    load_skills,
    load_skills_from_dir,
    search_skills,
)

# Phase 8: 高级功能
from coding_agent.prompt_templates import (
    CODE_REVIEW_TEMPLATE,
    DEBUGGING_TEMPLATE,
    REFACTORING_TEMPLATE,
    PromptTemplate,
    create_prompt_template,
    expand_prompt_template,
    expand_template_string,
    get_builtin_template,
    list_builtin_templates,
)
from coding_agent.slash_commands import (
    SlashCommand,
    SlashCommandRegistry,
    create_default_registry,
    parse_slash_command,
)
from coding_agent.resource_loader import (
    DefaultResourceLoader,
    InMemoryResourceLoader,
    ResourceLoader,
    ResourceNotFoundError,
)
from coding_agent.package_manager import (
    DefaultPackageManager,
    NoOpPackageManager,
    PackageInfo,
    PackageManager,
)

# Phase 9: 认证与授权
from coding_agent.auth_storage import (
    ApiKeyCredentials,
    AuthStorage,
    AuthStorageBackend,
    FileAuthStorageBackend,
    InMemoryAuthStorageBackend,
    OAuthCredentials,
)

__all__ = [
    "__version__",
    # AgentSession
    "AgentSession",
    "AgentSessionConfig",
    "PromptOptions",
    # Bash 执行器
    "BashResult",
    "execute_bash",
    # 消息
    "COMPACTION_SUMMARY_PREFIX",
    "COMPACTION_SUMMARY_SUFFIX",
    "BRANCH_SUMMARY_PREFIX",
    "BRANCH_SUMMARY_SUFFIX",
    "BashExecutionMessage",
    "CustomMessage",
    "BranchSummaryMessage",
    "CompactionSummaryMessage",
    "ExtendedMessage",
    "bash_execution_to_text",
    "convert_to_llm",
    "create_branch_summary_message",
    "create_compaction_summary_message",
    "create_custom_message",
    # 模型注册表
    "ModelInfo",
    "ModelRegistry",
    # 设置管理
    "CompactionSettings",
    "RetrySettings",
    "Settings",
    "SettingsError",
    "SettingsManager",
    # 系统提示
    "TOOL_DESCRIPTIONS",
    "BuildSystemPromptOptions",
    "build_system_prompt",
    # 压缩与上下文管理
    "FileOperations",
    "create_file_ops",
    "extract_file_ops_from_message",
    "compute_file_lists",
    "format_file_operations",
    "TOOL_RESULT_MAX_CHARS",
    "serialize_conversation",
    "SUMMARIZATION_SYSTEM_PROMPT",
    "CompactionConfigSettings",
    "DEFAULT_COMPACTION_SETTINGS",
    "calculate_context_tokens",
    "estimate_tokens",
    "estimate_context_tokens",
    "should_compact",
    "CompactionDetails",
    "CompactionResult",
    "PrepareCompactionResult",
    "prepare_compaction",
    "compact",
    "BranchSummaryResult",
    "BranchSummaryDetails",
    "BranchPreparation",
    "CollectEntriesResult",
    "collect_entries_for_branch_summary",
    "prepare_branch_summary",
    "generate_branch_summary",
    # SDK
    "create_coding_tools",
    "create_read_only_tools",
    "create_agent_session",
    "CreateAgentSessionOptions",
    "CreateAgentSessionResult",
    # 扩展系统
    "Extension",
    "ExtensionContext",
    "ExtensionRunner",
    "ToolDefinition",
    "clear_registered_tools",
    "discover_extensions",
    "get_wrapped_tools",
    "load_extension",
    "load_extensions",
    "register_tool",
    "unregister_tool",
    "wrap_registered_tool",
    "wrap_registered_tools",
    # 技能系统
    "Skill",
    "format_skill_for_prompt",
    "format_skills_for_prompt",
    "get_skill_by_tag",
    "load_skills",
    "load_skills_from_dir",
    "search_skills",
    # 高级功能 - 提示模板
    "PromptTemplate",
    "CODE_REVIEW_TEMPLATE",
    "DEBUGGING_TEMPLATE",
    "REFACTORING_TEMPLATE",
    "create_prompt_template",
    "expand_prompt_template",
    "expand_template_string",
    "get_builtin_template",
    "list_builtin_templates",
    # 高级功能 - 斜杠命令
    "SlashCommand",
    "SlashCommandRegistry",
    "create_default_registry",
    "parse_slash_command",
    # 高级功能 - 资源加载器
    "ResourceLoader",
    "DefaultResourceLoader",
    "InMemoryResourceLoader",
    "ResourceNotFoundError",
    # 高级功能 - 包管理器
    "PackageManager",
    "DefaultPackageManager",
    "NoOpPackageManager",
    "PackageInfo",
    # 认证与授权
    "AuthStorage",
    "AuthStorageBackend",
    "FileAuthStorageBackend",
    "InMemoryAuthStorageBackend",
    "ApiKeyCredentials",
    "OAuthCredentials",
]
