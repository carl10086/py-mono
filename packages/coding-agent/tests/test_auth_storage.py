from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

from coding_agent.auth_storage import (
    ApiKeyCredentials,
    AuthStorage,
    FileAuthStorageBackend,
    InMemoryAuthStorageBackend,
    OAuthCredentials,
)


def test_in_memory_auth_storage():
    mem_backend = InMemoryAuthStorageBackend()
    storage = AuthStorage(mem_backend)

    storage.save_api_key(
        key="openai-api",
        api_key="sk-test123456789",
        name="OpenAI API Key",
        provider="openai",
        created_at=datetime.now().isoformat(),
    )

    storage.save_oauth(
        key="github-oauth",
        access_token="gho_access123",
        refresh_token="gho_refresh456",
        expires_at=1700000000,
        provider="github",
        scope="repo,user",
    )

    assert len(storage.list_keys()) == 2
    assert "openai-api" in storage.list_api_keys()
    assert "github-oauth" in storage.list_oauth()

    api_key = storage.get_api_key("openai-api")
    assert api_key is not None
    assert api_key.name == "OpenAI API Key"
    assert api_key.provider == "openai"

    oauth = storage.get_oauth("github-oauth")
    assert oauth is not None
    assert oauth.provider == "github"
    assert oauth.scope == "repo,user"


def test_file_auth_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "auth.json"
        file_backend = FileAuthStorageBackend(storage_path)
        file_storage = AuthStorage(file_backend)

        file_storage.save_api_key(
            key="anthropic-api",
            api_key="sk-ant-test987",
            name="Anthropic API Key",
            provider="anthropic",
            created_at=datetime.now().isoformat(),
        )

        assert len(file_storage.list_keys()) == 1
        assert storage_path.exists()

        file_storage2 = AuthStorage(FileAuthStorageBackend(storage_path))
        assert len(file_storage2.list_keys()) == 1

        anthropic = file_storage2.get_api_key("anthropic-api")
        assert anthropic is not None
        assert anthropic.name == "Anthropic API Key"


def test_auth_storage_delete():
    mem_backend = InMemoryAuthStorageBackend()
    storage = AuthStorage(mem_backend)

    storage.save_api_key(
        key="openai-api",
        api_key="sk-test123456789",
        name="OpenAI API Key",
        provider="openai",
        created_at=datetime.now().isoformat(),
    )

    assert len(storage.list_keys()) == 1

    storage.delete("openai-api")
    assert len(storage.list_keys()) == 0
    assert not storage.exists("openai-api")


def test_auth_storage_get_nonexistent():
    mem_backend = InMemoryAuthStorageBackend()
    storage = AuthStorage(mem_backend)

    missing = storage.get_api_key("nonexistent")
    assert missing is None


def test_api_key_credentials():
    api_creds = ApiKeyCredentials(
        key="sk-demo",
        name="Demo Key",
        provider="demo",
        created_at="2024-01-01T00:00:00",
    )
    assert api_creds.name == "Demo Key"
    assert api_creds.provider == "demo"
    assert len(api_creds.key) == 7


def test_oauth_credentials():
    oauth_creds = OAuthCredentials(
        access_token="token123",
        refresh_token="refresh456",
        expires_at=1700000000,
        provider="demo",
        scope="read",
    )
    assert oauth_creds.provider == "demo"
    assert oauth_creds.scope == "read"
    assert oauth_creds.refresh_token is not None
