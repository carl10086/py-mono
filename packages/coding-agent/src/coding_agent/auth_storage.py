"""认证存储系统 - API Key 和 OAuth 凭证管理

提供安全的凭证存储和管理功能。
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)


# ============================================================================
# 凭证类型定义
# ============================================================================


@dataclass
class ApiKeyCredentials:
    """API Key 凭证。

    属性：
        key: API Key
        name: 凭证名称
        provider: 提供商（如 openai, anthropic）
        created_at: 创建时间
    """

    key: str
    name: str
    provider: str
    created_at: str


@dataclass
class OAuthCredentials:
    """OAuth 凭证。

    属性：
        access_token: 访问令牌
        refresh_token: 刷新令牌
        expires_at: 过期时间戳
        provider: OAuth 提供商
        scope: 授权范围
    """

    access_token: str
    refresh_token: str | None
    expires_at: int | None
    provider: str
    scope: str


# 凭证类型别名
Credentials = ApiKeyCredentials | OAuthCredentials


# ============================================================================
# 存储后端接口
# ============================================================================


class AuthStorageBackend(ABC):
    """认证存储后端接口。"""

    @abstractmethod
    def save(
        self,
        key: str,
        credentials: Credentials,
    ) -> bool:
        """保存凭证。

        Args:
            key: 凭证标识符
            credentials: 凭证对象

        Returns:
            是否保存成功
        """
        ...

    @abstractmethod
    def load(
        self,
        key: str,
    ) -> Credentials | None:
        """加载凭证。

        Args:
            key: 凭证标识符

        Returns:
            凭证对象或 None
        """
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除凭证。

        Args:
            key: 凭证标识符

        Returns:
            是否删除成功
        """
        ...

    @abstractmethod
    def list_keys(self) -> list[str]:
        """列出所有凭证键。

        Returns:
            凭证键列表
        """
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查凭证是否存在。

        Args:
            key: 凭证标识符

        Returns:
            是否存在
        """
        ...


# ============================================================================
# 文件存储后端
# ============================================================================


class FileAuthStorageBackend(AuthStorageBackend):
    """文件存储后端。

    将凭证存储在 JSON 文件中。

    属性：
        storage_path: 存储文件路径
    """

    def __init__(
        self,
        storage_path: Path | str,
    ) -> None:
        """初始化文件后端。

        Args:
            storage_path: 存储文件路径
        """
        self.storage_path = Path(storage_path)
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """确保存储目录和文件存在。"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("{}", encoding="utf-8")

    def _load_data(self) -> dict[str, Any]:
        """加载所有数据。

        Returns:
            存储的数据字典
        """
        try:
            content = self.storage_path.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception as e:
            logger.error(f"加载存储文件失败: {e}")
            return {}

    def _save_data(self, data: dict[str, Any]) -> bool:
        """保存所有数据。

        Args:
            data: 要保存的数据

        Returns:
            是否保存成功
        """
        try:
            self.storage_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return True
        except Exception as e:
            logger.error(f"保存存储文件失败: {e}")
            return False

    def _credentials_to_dict(self, credentials: Credentials) -> dict[str, Any]:
        """将凭证转换为字典。

        Args:
            credentials: 凭证对象

        Returns:
            字典表示
        """
        data = asdict(credentials)
        data["_type"] = "api_key" if isinstance(credentials, ApiKeyCredentials) else "oauth"
        return data

    def _dict_to_credentials(
        self,
        data: dict[str, Any],
    ) -> Credentials | None:
        """将字典转换为凭证。

        Args:
            data: 字典数据

        Returns:
            凭证对象或 None
        """
        cred_type = data.pop("_type", None)

        if cred_type == "api_key":
            return ApiKeyCredentials(**data)
        elif cred_type == "oauth":
            return OAuthCredentials(**data)
        else:
            logger.warning(f"未知的凭证类型: {cred_type}")
            return None

    def save(
        self,
        key: str,
        credentials: Credentials,
    ) -> bool:
        """保存凭证。"""
        data = self._load_data()
        data[key] = self._credentials_to_dict(credentials)
        return self._save_data(data)

    def load(self, key: str) -> Credentials | None:
        """加载凭证。"""
        data = self._load_data()

        if key not in data:
            return None

        return self._dict_to_credentials(data[key])

    def delete(self, key: str) -> bool:
        """删除凭证。"""
        data = self._load_data()

        if key not in data:
            return False

        del data[key]
        return self._save_data(data)

    def list_keys(self) -> list[str]:
        """列出所有凭证键。"""
        data = self._load_data()
        return list(data.keys())

    def exists(self, key: str) -> bool:
        """检查凭证是否存在。"""
        data = self._load_data()
        return key in data


# ============================================================================
# 内存存储后端
# ============================================================================


class InMemoryAuthStorageBackend(AuthStorageBackend):
    """内存存储后端。

    数据仅在内存中，重启后丢失。用于测试。
    """

    def __init__(self) -> None:
        """初始化内存后端。"""
        self._storage: dict[str, Credentials] = {}

    def save(
        self,
        key: str,
        credentials: Credentials,
    ) -> bool:
        """保存凭证。"""
        self._storage[key] = credentials
        return True

    def load(self, key: str) -> Credentials | None:
        """加载凭证。"""
        return self._storage.get(key)

    def delete(self, key: str) -> bool:
        """删除凭证。"""
        if key in self._storage:
            del self._storage[key]
            return True
        return False

    def list_keys(self) -> list[str]:
        """列出所有凭证键。"""
        return list(self._storage.keys())

    def exists(self, key: str) -> bool:
        """检查凭证是否存在。"""
        return key in self._storage


# ============================================================================
# 认证存储主类
# ============================================================================


class AuthStorage:
    """认证存储主类。

    提供统一的凭证管理接口。

    属性：
        backend: 存储后端
    """

    def __init__(
        self,
        backend: AuthStorageBackend | None = None,
    ) -> None:
        """初始化认证存储。

        Args:
            backend: 存储后端，None 使用内存后端
        """
        self.backend = backend or InMemoryAuthStorageBackend()

    def save_api_key(
        self,
        key: str,
        api_key: str,
        name: str,
        provider: str,
        created_at: str,
    ) -> bool:
        """保存 API Key。

        Args:
            key: 凭证标识符
            api_key: API Key 值
            name: 凭证名称
            provider: 提供商
            created_at: 创建时间

        Returns:
            是否保存成功
        """
        credentials = ApiKeyCredentials(
            key=api_key,
            name=name,
            provider=provider,
            created_at=created_at,
        )
        return self.backend.save(key, credentials)

    def save_oauth(
        self,
        key: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: int | None,
        provider: str,
        scope: str,
    ) -> bool:
        """保存 OAuth 凭证。

        Args:
            key: 凭证标识符
            access_token: 访问令牌
            refresh_token: 刷新令牌
            expires_at: 过期时间戳
            provider: OAuth 提供商
            scope: 授权范围

        Returns:
            是否保存成功
        """
        credentials = OAuthCredentials(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            provider=provider,
            scope=scope,
        )
        return self.backend.save(key, credentials)

    def get_api_key(self, key: str) -> ApiKeyCredentials | None:
        """获取 API Key 凭证。

        Args:
            key: 凭证标识符

        Returns:
            API Key 凭证或 None
        """
        creds = self.backend.load(key)
        if isinstance(creds, ApiKeyCredentials):
            return creds
        return None

    def get_oauth(self, key: str) -> OAuthCredentials | None:
        """获取 OAuth 凭证。

        Args:
            key: 凭证标识符

        Returns:
            OAuth 凭证或 None
        """
        creds = self.backend.load(key)
        if isinstance(creds, OAuthCredentials):
            return creds
        return None

    def delete(self, key: str) -> bool:
        """删除凭证。

        Args:
            key: 凭证标识符

        Returns:
            是否删除成功
        """
        return self.backend.delete(key)

    def list_keys(self) -> list[str]:
        """列出所有凭证键。"""
        return self.backend.list_keys()

    def list_api_keys(self) -> list[str]:
        """列出所有 API Key 凭证键。"""
        return [
            key
            for key in self.backend.list_keys()
            if isinstance(self.backend.load(key), ApiKeyCredentials)
        ]

    def list_oauth(self) -> list[str]:
        """列出所有 OAuth 凭证键。"""
        return [
            key
            for key in self.backend.list_keys()
            if isinstance(self.backend.load(key), OAuthCredentials)
        ]

    def exists(self, key: str) -> bool:
        """检查凭证是否存在。"""
        return self.backend.exists(key)
