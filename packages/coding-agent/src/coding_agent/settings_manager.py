"""设置管理模块 - 对齐 pi-mono TypeScript 实现（简化版）

提供配置的加载、保存和管理功能，支持全局和项目级别设置。

简化说明：
- 核心功能完整实现
- 移除了文件锁（Python的proper-lockfile跨平台复杂）
- 保留了设置结构和主要API
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from coding_agent.config import get_agent_dir


# ============================================================================
# 设置类型定义
# ============================================================================


@dataclass
class CompactionSettings:
    """压缩设置"""

    enabled: bool = True
    reserve_tokens: int = 16384
    keep_recent_tokens: int = 20000


@dataclass
class BranchSummarySettings:
    """分支摘要设置"""

    reserve_tokens: int = 16384
    skip_prompt: bool = False


@dataclass
class RetrySettings:
    """重试设置"""

    enabled: bool = True
    max_retries: int = 3
    base_delay_ms: int = 2000
    max_delay_ms: int = 60000


@dataclass
class TerminalSettings:
    """终端设置"""

    show_images: bool = True
    clear_on_shrink: bool = False


@dataclass
class ImageSettings:
    """图像设置"""

    auto_resize: bool = True
    block_images: bool = False


@dataclass
class ThinkingBudgetsSettings:
    """思考预算设置"""

    minimal: int | None = None
    low: int | None = None
    medium: int | None = None
    high: int | None = None


@dataclass
class MarkdownSettings:
    """Markdown设置"""

    code_block_indent: str = "  "


# 包源类型
PackageSource = str | dict[str, Any]


@dataclass
class Settings:
    """完整设置"""

    last_changelog_version: str | None = None
    default_provider: str | None = None
    default_model: str | None = None
    default_thinking_level: Literal["off", "minimal", "low", "medium", "high", "xhigh"] | None = (
        None
    )
    transport: Literal["sse", "websocket", "auto"] = "sse"
    steering_mode: Literal["all", "one-at-a-time"] = "one-at-a-time"
    follow_up_mode: Literal["all", "one-at-a-time"] = "one-at-a-time"
    theme: str | None = None
    compaction: CompactionSettings = field(default_factory=CompactionSettings)
    branch_summary: BranchSummarySettings = field(default_factory=BranchSummarySettings)
    retry: RetrySettings = field(default_factory=RetrySettings)
    hide_thinking_block: bool = False
    shell_path: str | None = None
    quiet_startup: bool = False
    shell_command_prefix: str | None = None
    npm_command: list[str] | None = None
    collapse_changelog: bool = False
    packages: list[PackageSource] = field(default_factory=list)
    extensions: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    enable_skill_commands: bool = True
    terminal: TerminalSettings = field(default_factory=TerminalSettings)
    images: ImageSettings = field(default_factory=ImageSettings)
    enabled_models: list[str] | None = None
    double_escape_action: Literal["fork", "tree", "none"] = "tree"
    tree_filter_mode: Literal["default", "no-tools", "user-only", "labeled-only", "all"] = "default"
    thinking_budgets: ThinkingBudgetsSettings | None = None
    editor_padding_x: int = 0
    autocomplete_max_visible: int = 5
    show_hardware_cursor: bool = False
    markdown: MarkdownSettings = field(default_factory=MarkdownSettings)


SettingsScope = Literal["global", "project"]


@dataclass
class SettingsError:
    """设置错误"""

    scope: SettingsScope
    error: Exception


# ============================================================================
# 设置管理器
# ============================================================================


class SettingsManager:
    """设置管理器

    管理全局和项目级别设置，支持：
    - 从文件加载设置
    - 保存设置到文件
    - 设置合并和覆盖
    """

    def __init__(
        self,
        global_settings: Settings,
        project_settings: Settings,
        global_path: Path,
        project_path: Path,
    ) -> None:
        """初始化设置管理器

        Args:
            global_settings: 全局设置
            project_settings: 项目设置
            global_path: 全局设置文件路径
            project_path: 项目设置文件路径
        """
        self._global_settings = global_settings
        self._project_settings = project_settings
        self._global_path = global_path
        self._project_path = project_path
        self._errors: list[SettingsError] = []
        self._modified_global: set[str] = set()
        self._modified_project: set[str] = set()

        # 合并设置（项目设置覆盖全局设置）
        self._settings = self._merge_settings(global_settings, project_settings)

    @staticmethod
    def _merge_settings(global_settings: Settings, project_settings: Settings) -> Settings:
        """合并全局和项目设置"""
        # 创建全局设置的副本
        merged = Settings(**{k: v for k, v in global_settings.__dict__.items()})

        # 用项目设置覆盖
        for key, value in project_settings.__dict__.items():
            if value is not None:
                if key in (
                    "compaction",
                    "branch_summary",
                    "retry",
                    "terminal",
                    "images",
                    "markdown",
                ):
                    # 嵌套对象特殊处理
                    if value is not None:
                        setattr(merged, key, value)
                else:
                    setattr(merged, key, value)

        return merged

    @staticmethod
    def _settings_to_dict(settings: Settings) -> dict[str, Any]:
        """将设置转换为字典"""
        result: dict[str, Any] = {}
        for key, value in settings.__dict__.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool, list, dict)):
                result[key] = value
            else:
                # dataclass
                result[key] = value.__dict__ if hasattr(value, "__dict__") else value
        return result

    @staticmethod
    def _dict_to_settings(data: dict[str, Any]) -> Settings:
        """将字典转换为设置"""
        # 处理嵌套对象
        if "compaction" in data and isinstance(data["compaction"], dict):
            data["compaction"] = CompactionSettings(**data["compaction"])
        if "branch_summary" in data and isinstance(data["branch_summary"], dict):
            data["branch_summary"] = BranchSummarySettings(**data["branch_summary"])
        if "retry" in data and isinstance(data["retry"], dict):
            data["retry"] = RetrySettings(**data["retry"])
        if "terminal" in data and isinstance(data["terminal"], dict):
            data["terminal"] = TerminalSettings(**data["terminal"])
        if "images" in data and isinstance(data["images"], dict):
            data["images"] = ImageSettings(**data["images"])
        if "thinking_budgets" in data and isinstance(data["thinking_budgets"], dict):
            data["thinking_budgets"] = ThinkingBudgetsSettings(**data["thinking_budgets"])
        if "markdown" in data and isinstance(data["markdown"], dict):
            data["markdown"] = MarkdownSettings(**data["markdown"])

        return Settings(**{k: v for k, v in data.items() if hasattr(Settings, k)})

    @staticmethod
    def _load_settings_file(path: Path) -> tuple[Settings, Exception | None]:
        """从文件加载设置"""
        if not path.exists():
            return Settings(), None

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            settings = SettingsManager._dict_to_settings(data)
            return settings, None
        except Exception as e:
            return Settings(), e

    def _save_settings_file(self, path: Path, settings: Settings) -> Exception | None:
        """保存设置到文件"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = self._settings_to_dict(settings)
            content = json.dumps(data, indent=2, ensure_ascii=False)
            path.write_text(content, encoding="utf-8")
            return None
        except Exception as e:
            return e

    @classmethod
    def create(cls, cwd: str | None = None, agent_dir: str | None = None) -> SettingsManager:
        """创建设置管理器（从文件加载）

        Args:
            cwd: 工作目录
            agent_dir: Agent 目录

        Returns:
            SettingsManager 实例
        """
        cwd = cwd or str(Path.cwd())
        agent_dir = agent_dir or get_agent_dir()

        global_path = Path(agent_dir) / "settings.json"
        project_path = Path(cwd) / ".pi" / "settings.json"

        global_settings, global_error = cls._load_settings_file(global_path)
        project_settings, project_error = cls._load_settings_file(project_path)

        manager = cls(global_settings, project_settings, global_path, project_path)

        if global_error:
            manager._errors.append(SettingsError("global", global_error))
        if project_error:
            manager._errors.append(SettingsError("project", project_error))

        return manager

    @classmethod
    def in_memory(cls, settings: Settings | None = None) -> SettingsManager:
        """创建内存中的设置管理器（不读写文件）

        Args:
            settings: 初始设置

        Returns:
            SettingsManager 实例
        """
        settings = settings or Settings()
        return cls(settings, Settings(), Path(), Path())

    # ============================================================================
    # 设置访问方法
    # ============================================================================

    def get_settings(self) -> Settings:
        """获取合并后的设置"""
        return self._settings

    def get_global_settings(self) -> Settings:
        """获取全局设置"""
        return self._global_settings

    def get_project_settings(self) -> Settings:
        """获取项目设置"""
        return self._project_settings

    # ============================================================================
    # 设置修改方法
    # ============================================================================

    def set_global(self, key: str, value: Any) -> None:
        """设置全局设置值"""
        setattr(self._global_settings, key, value)
        self._modified_global.add(key)
        self._settings = self._merge_settings(self._global_settings, self._project_settings)

    def set_project(self, key: str, value: Any) -> None:
        """设置项目设置值"""
        setattr(self._project_settings, key, value)
        self._modified_project.add(key)
        self._settings = self._merge_settings(self._global_settings, self._project_settings)

    # ============================================================================
    # 特定设置访问器
    # ============================================================================

    def get_default_provider(self) -> str | None:
        """获取默认提供商"""
        return self._settings.default_provider

    def get_default_model(self) -> str | None:
        """获取默认模型"""
        return self._settings.default_model

    def get_default_thinking_level(
        self,
    ) -> Literal["off", "minimal", "low", "medium", "high", "xhigh"] | None:
        """获取默认思考级别"""
        return self._settings.default_thinking_level

    def get_transport(self) -> Literal["sse", "websocket", "auto"]:
        """获取传输方式"""
        return self._settings.transport

    def get_steering_mode(self) -> Literal["all", "one-at-a-time"]:
        """获取转向模式"""
        return self._settings.steering_mode

    def get_follow_up_mode(self) -> Literal["all", "one-at-a-time"]:
        """获取跟进模式"""
        return self._settings.follow_up_mode

    def get_compaction_settings(self) -> CompactionSettings:
        """获取压缩设置"""
        return self._settings.compaction

    def get_retry_settings(self) -> RetrySettings:
        """获取重试设置"""
        return self._settings.retry

    def get_theme(self) -> str | None:
        """获取主题"""
        return self._settings.theme

    def get_shell_path(self) -> str | None:
        """获取 shell 路径"""
        return self._settings.shell_path

    # ============================================================================
    # 设置特定修改器
    # ============================================================================

    def set_default_provider(self, provider: str) -> None:
        """设置默认提供商"""
        self.set_global("default_provider", provider)

    def set_default_model(self, model: str) -> None:
        """设置默认模型"""
        self.set_global("default_model", model)

    def set_default_thinking_level(
        self, level: Literal["off", "minimal", "low", "medium", "high", "xhigh"]
    ) -> None:
        """设置默认思考级别"""
        self.set_global("default_thinking_level", level)

    def set_theme(self, theme: str) -> None:
        """设置主题"""
        self.set_global("theme", theme)

    def set_compaction_enabled(self, enabled: bool) -> None:
        """设置压缩启用状态"""
        self._global_settings.compaction.enabled = enabled
        self._modified_global.add("compaction")
        self._settings = self._merge_settings(self._global_settings, self._project_settings)

    def set_retry_enabled(self, enabled: bool) -> None:
        """设置重试启用状态"""
        self._global_settings.retry.enabled = enabled
        self._modified_global.add("retry")
        self._settings = self._merge_settings(self._global_settings, self._project_settings)

    # ============================================================================
    # 保存和错误处理
    # ============================================================================

    def save(self) -> list[SettingsError]:
        """保存设置到文件

        Returns:
            错误列表（如果有）
        """
        errors: list[SettingsError] = []

        # 保存全局设置
        if self._modified_global and self._global_path:
            error = self._save_settings_file(self._global_path, self._global_settings)
            if error:
                errors.append(SettingsError("global", error))
            else:
                self._modified_global.clear()

        # 保存项目设置
        if self._modified_project and self._project_path:
            error = self._save_settings_file(self._project_path, self._project_settings)
            if error:
                errors.append(SettingsError("project", error))
            else:
                self._modified_project.clear()

        return errors

    def drain_errors(self) -> list[SettingsError]:
        """获取并清空错误列表"""
        errors = self._errors[:]
        self._errors = []
        return errors


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 设置类型
    "CompactionSettings",
    "BranchSummarySettings",
    "RetrySettings",
    "TerminalSettings",
    "ImageSettings",
    "ThinkingBudgetsSettings",
    "MarkdownSettings",
    "PackageSource",
    "Settings",
    "SettingsScope",
    "SettingsError",
    # 管理器
    "SettingsManager",
]
