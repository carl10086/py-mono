from __future__ import annotations

import os
import tempfile

from coding_agent.tools.path_utils import (
    is_path_inside,
    normalize_path,
    resolve_to_cwd,
    validate_path,
)


def test_normalize_path() -> None:
    assert normalize_path("/foo/bar") == "/foo/bar"
    assert normalize_path("  /foo/bar  ") == "/foo/bar"
    assert normalize_path("@/foo/bar") == "/foo/bar"
    home = os.path.expanduser("~")
    assert normalize_path("~") == home
    assert normalize_path("~/test") == home + "/test"


def test_resolve_to_cwd() -> None:
    cwd = "/home/user/project"
    assert resolve_to_cwd("/absolute/path", cwd) == "/absolute/path"
    assert resolve_to_cwd("relative/path", cwd) == "/home/user/project/relative/path"
    home = os.path.expanduser("~")
    assert resolve_to_cwd("~/test", cwd) == f"{home}/test"


def test_is_path_inside() -> None:
    root = "/home/user"
    assert is_path_inside("/home/user", "/home/user") is True
    assert is_path_inside("/home/user/project", "/home/user") is True
    assert is_path_inside("/home/user/a/b/c", "/home/user") is True
    assert is_path_inside("/home/user/../../../etc/passwd", "/home/user") is False
    assert is_path_inside("/home/other", "/home/user") is False
    assert is_path_inside("/home/username", "/home/user") is False


def test_validate_path() -> None:
    cwd = os.getcwd()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"test content")
        tmp_path = tmp.name

    tmp_dir = os.path.dirname(tmp_path)

    try:
        result = validate_path(tmp_path, cwd)
        assert os.path.isabs(result)

        result = validate_path(tmp_path, cwd, require_exists=True)
        assert result == tmp_path

        with tempfile.NamedTemporaryFile(delete=False) as nonexist:
            pass
        try:
            validate_path(nonexist.name, cwd, require_exists=True)
            assert False, "should raise FileNotFoundError"
        except FileNotFoundError:
            pass
        finally:
            os.unlink(nonexist.name)

        allowed_roots = [tmp_dir, cwd]
        result = validate_path(tmp_path, cwd, allowed_roots=allowed_roots)
        assert result == tmp_path

        try:
            validate_path("/etc/passwd", cwd, allowed_roots=allowed_roots)
            assert False, "should raise PermissionError"
        except PermissionError:
            pass

    finally:
        os.unlink(tmp_path)
