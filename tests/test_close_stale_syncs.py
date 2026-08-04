"""Unit tests for scripts/close_stale_syncs.py.
Run with: .venv/aw/bin/python -m pytest repos/aw-marketplace/tests/test_close_stale_syncs.py
"""
import base64
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from close_stale_syncs import close_stale_syncs  # noqa: E402


def _b64_apps(apps):
    return base64.b64encode(json.dumps({"apps": apps}).encode()).decode()


class _FakeResponses:
    """Programs urllib.request.urlopen's return value in call order."""

    def __init__(self, monkeypatch, routes):
        # routes: dict[(method, path_prefix)] -> response payload (dict)
        self.routes = routes
        self.calls = []
        monkeypatch.setattr("close_stale_syncs.urllib.request.urlopen", self._urlopen)

    def _urlopen(self, req):
        method = req.get_method()
        url = req.full_url
        self.calls.append((method, url))
        for (m, prefix), payload in self.routes.items():
            if m == method and prefix in url:
                body = json.dumps(payload).encode() if payload is not None else b""
                return _FakeResponse(body)
        raise AssertionError(f"unmocked request: {method} {url}")


class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_closes_pr_whose_version_is_already_in_master(monkeypatch):
    master_apps = [{"id": "mcp-gateway", "version": "0.6.0"}]
    pr_apps = [{"id": "mcp-gateway", "version": "0.5.3"}]
    routes = {
        ("GET", "/contents/apps.json?ref=master"): {"content": _b64_apps(master_apps)},
        ("GET", "/pulls?state=open"): [
            {"number": 70, "head": {"ref": "sync/mcp-gateway", "sha": "abc123"}},
        ],
        ("GET", "/contents/apps.json?ref=abc123"): {"content": _b64_apps(pr_apps)},
        ("POST", "/issues/70/comments"): {},
        ("PATCH", "/pulls/70"): {},
    }
    fake = _FakeResponses(monkeypatch, routes)

    closed = close_stale_syncs("tok", "tekflox/aw-marketplace")

    assert closed == [{"number": 70, "app_id": "mcp-gateway",
                        "pr_version": (0, 5, 3), "master_version": (0, 6, 0)}]
    methods = [m for m, _ in fake.calls]
    assert "PATCH" in methods and "POST" in methods


def test_leaves_pr_alone_when_it_is_still_ahead_of_master(monkeypatch):
    master_apps = [{"id": "tasks", "version": "0.9.0"}]
    pr_apps = [{"id": "tasks", "version": "0.10.0"}]
    routes = {
        ("GET", "/contents/apps.json?ref=master"): {"content": _b64_apps(master_apps)},
        ("GET", "/pulls?state=open"): [
            {"number": 93, "head": {"ref": "sync/tasks", "sha": "def456"}},
        ],
        ("GET", "/contents/apps.json?ref=def456"): {"content": _b64_apps(pr_apps)},
    }
    _FakeResponses(monkeypatch, routes)

    closed = close_stale_syncs("tok", "tekflox/aw-marketplace")

    assert closed == []


def test_ignores_non_sync_branches(monkeypatch):
    master_apps = [{"id": "tasks", "version": "0.9.0"}]
    routes = {
        ("GET", "/contents/apps.json?ref=master"): {"content": _b64_apps(master_apps)},
        ("GET", "/pulls?state=open"): [
            {"number": 5, "head": {"ref": "feature/some-app-work", "sha": "xyz"}},
        ],
    }
    _FakeResponses(monkeypatch, routes)

    closed = close_stale_syncs("tok", "tekflox/aw-marketplace")

    assert closed == []
