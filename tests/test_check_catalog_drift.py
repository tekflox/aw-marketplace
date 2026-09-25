"""Unit tests for scripts/check_catalog_drift.py.
Run with: .venv/aw/bin/python -m pytest repos/aw-marketplace/tests/test_check_catalog_drift.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from check_catalog_drift import (  # noqa: E402
    ISSUE_TITLE,
    find_drift,
    latest_repo_version,
    render_issue_body,
    report_drift,
)


def _catalog(*apps):
    return {"manifest_version": 1, "apps": list(apps)}


class _FakeResponses:
    """Programs urllib.request.urlopen's return value by (method, url substring)."""

    def __init__(self, monkeypatch, routes):
        self.routes = routes
        self.calls = []
        monkeypatch.setattr("check_catalog_drift.urllib.request.urlopen", self._urlopen)

    def _urlopen(self, req):
        method = req.get_method()
        url = req.full_url
        payload_sent = req.data and json.loads(req.data)
        self.calls.append((method, url, payload_sent))
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


# --- find_drift -----------------------------------------------------------


def test_reports_entry_behind_its_repo():
    catalog = _catalog({"id": "aw-app-uc-phd", "repo": "fredericowu/aw-app-uc-phd",
                        "version": "0.1.1"})

    assert find_drift(catalog, {"fredericowu/aw-app-uc-phd": "0.6.0"}) == [{
        "id": "aw-app-uc-phd",
        "repo": "fredericowu/aw-app-uc-phd",
        "catalog_version": "0.1.1",
        "repo_version": "0.6.0",
    }]


def test_entry_level_with_its_repo_is_not_drift():
    catalog = _catalog({"id": "git", "repo": "tekflox/aw-app-git", "version": "0.19.0"})

    assert find_drift(catalog, {"tekflox/aw-app-git": "0.19.0"}) == []


def test_entry_ahead_of_its_repo_is_not_drift():
    """A merged sync PR whose tag lookup lags (or a hand-synced entry) must not
    produce a recurring issue nobody can act on."""
    catalog = _catalog({"id": "git", "repo": "tekflox/aw-app-git", "version": "0.20.0"})

    assert find_drift(catalog, {"tekflox/aw-app-git": "0.19.0"}) == []


def test_unknown_or_unparseable_versions_are_skipped_not_reported():
    catalog = _catalog(
        {"id": "no-tags", "repo": "tekflox/aw-app-no-tags", "version": "0.1.0"},
        {"id": "weird", "repo": "tekflox/aw-app-weird", "version": "not-a-version"},
        {"id": "no-repo", "version": "0.1.0"},
    )
    latest = {"tekflox/aw-app-no-tags": None, "tekflox/aw-app-weird": "0.4.0"}

    assert find_drift(catalog, latest) == []


def test_reports_every_drifted_app_not_just_the_first():
    catalog = _catalog(
        {"id": "a", "repo": "tekflox/aw-app-a", "version": "1.0.0"},
        {"id": "b", "repo": "tekflox/aw-app-b", "version": "0.2.0"},
        {"id": "c", "repo": "tekflox/aw-app-c", "version": "0.3.0"},
    )
    latest = {"tekflox/aw-app-a": "1.0.1", "tekflox/aw-app-b": "0.2.0",
              "tekflox/aw-app-c": "1.0.0"}

    assert [d["id"] for d in find_drift(catalog, latest)] == ["a", "c"]


def test_minor_beats_patch_numerically_not_lexically():
    """0.10.0 > 0.9.0 — a string compare would call this "not drift"."""
    catalog = _catalog({"id": "a", "repo": "tekflox/aw-app-a", "version": "0.9.0"})

    assert find_drift(catalog, {"tekflox/aw-app-a": "0.10.0"})[0]["repo_version"] == "0.10.0"


# --- latest_repo_version --------------------------------------------------


def test_latest_repo_version_takes_the_highest_tag_not_the_first(monkeypatch):
    _FakeResponses(monkeypatch, {
        ("GET", "/repos/tekflox/aw-app-a/tags"): [
            {"name": "v0.2.0"}, {"name": "v0.10.0"}, {"name": "v0.9.3"},
            {"name": "not-a-tag"},
        ],
    })

    assert latest_repo_version("tok", "tekflox/aw-app-a") == "0.10.0"


def test_latest_repo_version_is_none_when_no_parseable_tag(monkeypatch):
    _FakeResponses(monkeypatch, {("GET", "/repos/tekflox/aw-app-a/tags"): []})

    assert latest_repo_version("tok", "tekflox/aw-app-a") is None


def test_latest_repo_version_survives_a_vanished_repo(monkeypatch):
    import urllib.error

    def _raise(req):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr("check_catalog_drift.urllib.request.urlopen", _raise)

    assert latest_repo_version("tok", "tekflox/aw-app-gone") is None


# --- issue lifecycle ------------------------------------------------------


def test_opens_one_issue_listing_every_drifted_app(monkeypatch):
    fake = _FakeResponses(monkeypatch, {
        ("GET", "/issues?state=open"): [],
        ("POST", "/issues"): {"number": 42},
    })
    drifted = [
        {"id": "a", "repo": "tekflox/aw-app-a", "catalog_version": "1.0.0",
         "repo_version": "1.0.1"},
        {"id": "b", "repo": "tekflox/aw-app-b", "catalog_version": "0.1.0",
         "repo_version": "0.6.0"},
    ]

    assert report_drift("tok", "tekflox/aw-marketplace", drifted) == {
        "action": "opened", "number": 42}
    posts = [c for c in fake.calls if c[0] == "POST"]
    assert len(posts) == 1, "one issue for all drifted apps, never one per app"
    body = posts[0][2]["body"]
    assert "`a`" in body and "`b`" in body


def test_updates_the_existing_issue_instead_of_opening_a_second(monkeypatch):
    fake = _FakeResponses(monkeypatch, {
        ("GET", "/issues?state=open"): [{"number": 7, "title": ISSUE_TITLE}],
        ("PATCH", "/issues/7"): {"number": 7},
    })
    drifted = [{"id": "a", "repo": "tekflox/aw-app-a", "catalog_version": "1.0.0",
                "repo_version": "1.0.1"}]

    assert report_drift("tok", "tekflox/aw-marketplace", drifted) == {
        "action": "updated", "number": 7}
    assert not [c for c in fake.calls if c[0] == "POST"]


def test_ignores_a_pull_request_that_shares_the_issue_title(monkeypatch):
    """/issues returns PRs too; patching one would rewrite a PR description."""
    fake = _FakeResponses(monkeypatch, {
        ("GET", "/issues?state=open"): [
            {"number": 9, "title": ISSUE_TITLE, "pull_request": {"url": "..."}},
        ],
        ("POST", "/issues"): {"number": 10},
    })
    drifted = [{"id": "a", "repo": "tekflox/aw-app-a", "catalog_version": "1.0.0",
                "repo_version": "1.0.1"}]

    assert report_drift("tok", "tekflox/aw-marketplace", drifted)["number"] == 10
    assert not [c for c in fake.calls if c[0] == "PATCH"]


def test_closes_the_issue_once_nothing_is_behind(monkeypatch):
    fake = _FakeResponses(monkeypatch, {
        ("GET", "/issues?state=open"): [{"number": 7, "title": ISSUE_TITLE}],
        ("POST", "/issues/7/comments"): {},
        ("PATCH", "/issues/7"): {"number": 7},
    })

    assert report_drift("tok", "tekflox/aw-marketplace", []) == {
        "action": "closed", "number": 7}
    assert [c[2] for c in fake.calls if c[0] == "PATCH"] == [{"state": "closed"}]


def test_no_drift_and_no_existing_issue_writes_nothing(monkeypatch):
    fake = _FakeResponses(monkeypatch, {("GET", "/issues?state=open"): []})

    assert report_drift("tok", "tekflox/aw-marketplace", []) == {"action": "none"}
    assert [c[0] for c in fake.calls] == ["GET"]


def test_issue_body_names_the_repo_and_both_versions():
    body = render_issue_body([{"id": "aw-app-uc-phd", "repo": "fredericowu/aw-app-uc-phd",
                               "catalog_version": "0.1.1", "repo_version": "0.6.0"}])

    assert "fredericowu/aw-app-uc-phd" in body
    assert "`0.1.1`" in body and "`0.6.0`" in body
    assert "MARKETPLACE_SYNC_TOKEN" in body
