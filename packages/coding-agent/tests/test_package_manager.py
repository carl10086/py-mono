from __future__ import annotations

from coding_agent.package_manager import (
    DefaultPackageManager,
    NoOpPackageManager,
    PackageInfo,
)


def test_noop_package_manager():
    noop = NoOpPackageManager()
    assert noop.install("requests") is False
    assert noop.uninstall("requests") is False
    assert noop.update("requests") is False
    assert noop.list_installed() == []
    assert noop.get_info("requests") is None
    assert noop.search("http") == []


def test_default_package_manager_list_installed():
    pm = DefaultPackageManager()
    installed = pm.list_installed()
    assert isinstance(installed, list)


def test_default_package_manager_get_info():
    pm = DefaultPackageManager()
    pip_info = pm.get_info("pip")
    if pip_info:
        assert pip_info.name == "pip"
        assert pip_info.version is not None


def test_package_info():
    info = PackageInfo(
        name="example-package",
        version="1.0.0",
        installed=True,
        latest_version="1.1.0",
        description="示例包",
    )
    assert info.name == "example-package"
    assert info.version == "1.0.0"
    assert info.installed is True
    assert info.latest_version == "1.1.0"
    assert info.description == "示例包"
