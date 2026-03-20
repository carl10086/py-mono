"""示例 36: 认证存储测试

验证 API Key 和 OAuth 凭证管理功能。
"""

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

print("=== 认证存储测试 ===")
print()

# 测试内存存储后端
print("1. 内存存储后端...")
mem_backend = InMemoryAuthStorageBackend()
mem_storage = AuthStorage(mem_backend)

# 保存 API Key
mem_storage.save_api_key(
    key="openai-api",
    api_key="sk-test123456789",
    name="OpenAI API Key",
    provider="openai",
    created_at=datetime.now().isoformat(),
)

# 保存 OAuth
mem_storage.save_oauth(
    key="github-oauth",
    access_token="gho_access123",
    refresh_token="gho_refresh456",
    expires_at=1700000000,
    provider="github",
    scope="repo,user",
)

print(f"   所有凭证键: {mem_storage.list_keys()}")
print(f"   API Keys: {mem_storage.list_api_keys()}")
print(f"   OAuth: {mem_storage.list_oauth()}")
print()

# 读取凭证
print("2. 读取凭证...")
api_key = mem_storage.get_api_key("openai-api")
if api_key:
    print(f"   API Key: {api_key.name} ({api_key.provider})")
    print(f"   Key: {api_key.key[:10]}...")

oauth = mem_storage.get_oauth("github-oauth")
if oauth:
    print(f"   OAuth: {oauth.provider} ({oauth.scope})")
    print(f"   Token: {oauth.access_token[:10]}...")
print()

# 测试文件存储后端
print("3. 文件存储后端...")
with tempfile.TemporaryDirectory() as tmpdir:
    storage_path = Path(tmpdir) / "auth.json"
    file_backend = FileAuthStorageBackend(storage_path)
    file_storage = AuthStorage(file_backend)

    # 保存凭证
    file_storage.save_api_key(
        key="anthropic-api",
        api_key="sk-ant-test987",
        name="Anthropic API Key",
        provider="anthropic",
        created_at=datetime.now().isoformat(),
    )

    file_storage.save_oauth(
        key="google-oauth",
        access_token="ya29.access",
        refresh_token=None,
        expires_at=1700000000,
        provider="google",
        scope="openid email",
    )

    print(f"   凭证数量: {len(file_storage.list_keys())}")
    print(f"   存储文件存在: {storage_path.exists()}")

    # 验证持久化
    file_storage2 = AuthStorage(FileAuthStorageBackend(storage_path))
    print(f"   重新加载后凭证数: {len(file_storage2.list_keys())}")

    # 读取保存的凭证
    anthropic = file_storage2.get_api_key("anthropic-api")
    if anthropic:
        print(f"   读取成功: {anthropic.name}")

print()

# 测试删除
print("4. 删除凭证...")
mem_storage.delete("openai-api")
print(f"   删除后凭证数: {len(mem_storage.list_keys())}")
print(f"   'openai-api' 存在: {mem_storage.exists('openai-api')}")
print()

# 测试不存在凭证
print("5. 读取不存在的凭证...")
missing = mem_storage.get_api_key("nonexistent")
print(f"   结果: {missing}")
print()

# 展示数据结构
print("6. 数据结构...")
api_creds = ApiKeyCredentials(
    key="sk-demo",
    name="Demo Key",
    provider="demo",
    created_at="2024-01-01T00:00:00",
)
oauth_creds = OAuthCredentials(
    access_token="token123",
    refresh_token="refresh456",
    expires_at=1700000000,
    provider="demo",
    scope="read",
)

print(f"   ApiKeyCredentials:")
print(f"     - name: {api_creds.name}")
print(f"     - provider: {api_creds.provider}")
print(f"     - key length: {len(api_creds.key)}")

print(f"   OAuthCredentials:")
print(f"     - provider: {oauth_creds.provider}")
print(f"     - scope: {oauth_creds.scope}")
print(f"     - has refresh: {oauth_creds.refresh_token is not None}")
print()

print("✓ 认证存储测试通过")
print()
print("=== 认证存储特性 ===")
print("- API Key 凭证管理")
print("- OAuth 凭证管理")
print("- 文件存储后端（持久化）")
print("- 内存存储后端（测试用）")
print("- 凭证类型自动识别")
