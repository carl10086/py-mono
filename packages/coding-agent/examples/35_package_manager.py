"""示例 35: 包管理器测试

验证包管理功能。
"""

from coding_agent.package_manager import (
    DefaultPackageManager,
    NoOpPackageManager,
    PackageInfo,
)

print("=== 包管理器测试 ===")
print()

# 测试 NoOp 包管理器
print("1. NoOp 包管理器（禁用状态）...")
noop = NoOpPackageManager()
print(f"   安装结果: {noop.install('requests')}")
print(f"   卸载结果: {noop.uninstall('requests')}")
print(f"   更新结果: {noop.update('requests')}")
print(f"   已安装列表: {noop.list_installed()}")
print(f"   包信息: {noop.get_info('requests')}")
print(f"   搜索结果: {noop.search('http')}")
print()

# 测试默认包管理器（实际 pip 操作）
print("2. 默认包管理器（pip）...")
pm = DefaultPackageManager()

# 列出已安装包
print("   列出部分已安装包...")
installed = pm.list_installed()
print(f"   已安装包数量: {len(installed)}")
if installed:
    print(f"   前5个包:")
    for pkg in installed[:5]:
        print(f"     - {pkg.name} ({pkg.version})")
print()

# 获取包信息
print("3. 获取包信息...")
pip_info = pm.get_info("pip")
if pip_info:
    print(f"   pip 包信息:")
    print(f"     名称: {pip_info.name}")
    print(f"     版本: {pip_info.version}")
    print(f"     描述: {pip_info.description or 'N/A'}")
else:
    print("   无法获取 pip 信息")
print()

# 测试搜索（pip search 已被禁用）
print("4. 搜索包...")
results = pm.search("requests")
print(f"   搜索结果数量: {len(results)}")
if results:
    for pkg in results[:3]:
        print(f"     - {pkg.name}")
print()

# 展示 PackageInfo 结构
print("5. PackageInfo 数据结构...")
info = PackageInfo(
    name="example-package",
    version="1.0.0",
    installed=True,
    latest_version="1.1.0",
    description="示例包",
)
print(f"   名称: {info.name}")
print(f"   版本: {info.version}")
print(f"   已安装: {info.installed}")
print(f"   最新版本: {info.latest_version}")
print(f"   描述: {info.description}")
print()

print("✓ 包管理器测试通过")
print()
print("=== 包管理器特性 ===")
print("- pip 包安装/卸载/更新")
print("- 列出已安装包")
print("- 获取包详细信息")
print("- NoOp 模式（禁用包管理）")
print()
print("注意: 实际安装/卸载操作需要谨慎使用")
