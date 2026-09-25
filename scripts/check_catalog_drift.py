#!/usr/bin/env python3
"""Report catalog entries whose version is behind their app repo's latest tag.

Why this exists: aw-app-uc-phd's entry sat at v0.1.1 for months while its repo
advanced to v0.6.0, because its release workflow could not run at all. Nothing
anywhere noticed — a frozen catalog entry is indistinguishable from an app that
simply has not been released lately. `aw-workspace-cli marketplace install
<app> --update` then silently reinstalls the ancient version, which reads as the
live app "reverting" for no reason.

Deliberately cause-agnostic. It checks the SYMPTOM (catalog behind repo) rather
than any particular reason for it — a missing credential, a runner a repo can
never reach, a release job someone disabled, a sync PR left unmerged. The
ownership fix in app-release.yml closes the known cause; this closes the ones
nobody has thought of yet.

Pure functions, no git/gh/network calls in the testable core (see
tests/test_check_catalog_drift.py) — same shape as close_stale_syncs.py. The
CLI wrapper at the bottom is what .github/workflows/catalog-drift.yml runs.

ONE issue, updated in place, listing every drifted app. One issue per app would
be the noise this is meant to cure, and ~57 repos' worth of API calls is
already the reason the tag lookup is a single request per app.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
ISSUE_TITLE = "Catalog drift: app entries behind their repo's latest release"
ISSUE_LABEL_MARKER = "<!-- aw-catalog-drift -->"


def _request(token: str, method: str, path: str, payload: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as response:
        body = response.read()
        return json.loads(body) if body else None


def _semver_tuple(version: str) -> tuple[int, int, int] | None:
    m = SEMVER_RE.match((version or "").strip().lstrip("v"))
    if not m:
        return None
    return tuple(int(p) for p in m.groups())


def latest_repo_version(token: str, repo: str) -> str | None:
    """Highest semver tag on `repo`, or None when it has none we can parse.

    Tags, not releases: this estate's release workflow pushes a `vX.Y.Z` tag
    and never creates a GitHub Release, so /releases/latest is empty for every
    app here.
    """
    try:
        tags = _request(token, "GET", f"/repos/{repo}/tags?per_page=100")
    except urllib.error.HTTPError:
        return None  # repo gone, renamed, or not visible to this token
    versions = [v for v in (_semver_tuple(t.get("name", "")) for t in tags or []) if v]
    if not versions:
        return None
    return ".".join(str(p) for p in max(versions))


def find_drift(catalog: dict, latest_versions: dict[str, str | None]) -> list[dict]:
    """Entries whose catalog version is strictly behind their repo's latest tag.

    `latest_versions` maps repo -> latest version string (or None), so the
    network lookup stays outside this function. Pure: nothing here mutates the
    catalog or touches the network.
    """
    drifted = []
    for entry in catalog.get("apps", []):
        app_id, repo = entry.get("id"), entry.get("repo")
        if not app_id or not repo:
            continue
        catalog_version = _semver_tuple(entry.get("version", ""))
        repo_version = _semver_tuple(latest_versions.get(repo) or "")
        # An unparseable/absent version on either side is not drift — it is a
        # question we cannot answer, and guessing would produce a recurring
        # issue nobody can close.
        if catalog_version is None or repo_version is None:
            continue
        if repo_version > catalog_version:
            drifted.append({
                "id": app_id,
                "repo": repo,
                "catalog_version": ".".join(str(p) for p in catalog_version),
                "repo_version": ".".join(str(p) for p in repo_version),
            })
    return drifted


def render_issue_body(drifted: list[dict]) -> str:
    """Markdown body for the single tracking issue."""
    lines = [
        ISSUE_LABEL_MARKER,
        "",
        "These `apps.json` entries are behind the latest `vX.Y.Z` tag on their "
        "own repo, so `aw-workspace-cli marketplace install <app> --update` "
        "installs the older version:",
        "",
        "| app | repo | catalog | repo latest |",
        "| --- | --- | --- | --- |",
    ]
    for d in drifted:
        lines.append(
            f"| `{d['id']}` | [{d['repo']}](https://github.com/{d['repo']}) | "
            f"`{d['catalog_version']}` | `{d['repo_version']}` |"
        )
    lines += [
        "",
        "Usual causes: the app's release workflow never ran (disabled trigger, "
        "a runner it cannot reach, a missing `MARKETPLACE_SYNC_TOKEN`), or its "
        "`sync/<app-id>` PR here is still open. Check the app repo's Actions "
        "tab and this repo's open PRs before re-syncing by hand with "
        "`scripts/sync_catalog_entry.py`.",
        "",
        "_Opened and updated automatically by "
        "`.github/workflows/catalog-drift.yml`. It closes itself when no entry "
        "is behind._",
    ]
    return "\n".join(lines)


def _find_existing_issue(token: str, repo: str) -> dict | None:
    issues = _request(token, "GET", f"/repos/{repo}/issues?state=open&per_page=100")
    for issue in issues or []:
        if "pull_request" in issue:
            continue
        if issue.get("title") == ISSUE_TITLE:
            return issue
    return None


def report_drift(token: str, repo: str, drifted: list[dict]) -> dict:
    """Open, update, or close the single drift issue. Returns what it did."""
    existing = _find_existing_issue(token, repo)

    if not drifted:
        if existing:
            _request(token, "POST", f"/repos/{repo}/issues/{existing['number']}/comments",
                     {"body": "No catalog entry is behind its repo any more — closing."})
            _request(token, "PATCH", f"/repos/{repo}/issues/{existing['number']}",
                     {"state": "closed"})
            return {"action": "closed", "number": existing["number"]}
        return {"action": "none"}

    body = render_issue_body(drifted)
    if existing:
        _request(token, "PATCH", f"/repos/{repo}/issues/{existing['number']}",
                 {"body": body})
        return {"action": "updated", "number": existing["number"]}
    issue = _request(token, "POST", f"/repos/{repo}/issues",
                     {"title": ISSUE_TITLE, "body": body})
    return {"action": "opened", "number": issue["number"]}


def main() -> int:
    token = os.environ["GH_TOKEN"]
    repo = os.environ.get("GH_REPOSITORY", "tekflox/aw-marketplace")
    catalog_path = os.environ.get("CATALOG_PATH", "apps.json")

    catalog = json.load(open(catalog_path))
    repos = sorted({e["repo"] for e in catalog.get("apps", []) if e.get("repo")})
    latest_versions = {r: latest_repo_version(token, r) for r in repos}

    drifted = find_drift(catalog, latest_versions)
    for d in drifted:
        print(f"drift: {d['id']} catalog {d['catalog_version']} < repo {d['repo_version']}")
    unknown = [r for r, v in latest_versions.items() if v is None]
    if unknown:
        print(f"no parseable tag (skipped, not reported as drift): {', '.join(unknown)}")
    if not drifted:
        print(f"no drift across {len(repos)} app repos")

    result = report_drift(token, repo, drifted)
    print(f"issue {result['action']}" + (f" #{result['number']}" if "number" in result else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
