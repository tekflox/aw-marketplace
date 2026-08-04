#!/usr/bin/env python3
"""Close open sync/* PRs whose version bump is already superseded by master.

Triggered on every pull_request event (opened/synchronize/reopened) instead
of a polling cron — cheaper and reacts immediately when a newer sync for the
same app lands and makes an older one redundant.

Safety: a PR is closed ONLY when master's apps.json already has a version
>= what the PR would bump to for that app_id (i.e. applying the PR would be
a no-op or a downgrade) — never based on git "behind" status, which just
means the branch needs updating, not that its content is stale. A PR that's
behind but still represents real forward progress (a version master doesn't
have yet) is left alone; GitHub's own auto-merge retries update it.
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
SYNC_BRANCH_RE = re.compile(r"^sync/(.+)$")


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
    m = SEMVER_RE.match((version or "").strip())
    if not m:
        return None
    return tuple(int(p) for p in m.groups())


def _apps_by_id(apps_json: dict) -> dict[str, dict]:
    apps = apps_json.get("apps", apps_json) if isinstance(apps_json, dict) else apps_json
    return {a["id"]: a for a in apps if isinstance(a, dict) and a.get("id")}


def _fetch_apps_json(token: str, repo: str, ref: str) -> dict:
    content = _request(token, "GET", f"/repos/{repo}/contents/apps.json?ref={ref}")
    import base64
    return json.loads(base64.b64decode(content["content"]))


def close_stale_syncs(token: str, repo: str) -> list[dict]:
    """Returns the list of PRs closed, for logging/testing."""
    master_apps = _apps_by_id(_fetch_apps_json(token, repo, "master"))
    prs = _request(token, "GET", f"/repos/{repo}/pulls?state=open&per_page=100")

    closed = []
    for pr in prs:
        branch = pr["head"]["ref"]
        m = SYNC_BRANCH_RE.match(branch)
        if not m:
            continue
        app_id = m.group(1)

        master_entry = master_apps.get(app_id)
        if not master_entry:
            continue  # app not in master yet — nothing to compare against
        master_version = _semver_tuple(master_entry.get("version", ""))
        if master_version is None:
            continue

        try:
            pr_apps = _apps_by_id(_fetch_apps_json(token, repo, pr["head"]["sha"]))
        except urllib.error.HTTPError:
            continue  # PR branch/commit vanished mid-run — skip, not our problem
        pr_entry = pr_apps.get(app_id)
        if not pr_entry:
            continue
        pr_version = _semver_tuple(pr_entry.get("version", ""))
        if pr_version is None:
            continue

        if master_version >= pr_version:
            _request(token, "POST", f"/repos/{repo}/issues/{pr['number']}/comments", {
                "body": (
                    f"Closing — master's `apps.json` already has `{app_id}` at "
                    f"`{'.'.join(map(str, master_version))}`, which is >= this "
                    f"PR's `{'.'.join(map(str, pr_version))}`. Superseded by a "
                    "later sync that merged first, nothing left to apply here."
                ),
            })
            _request(token, "PATCH", f"/repos/{repo}/pulls/{pr['number']}", {"state": "closed"})
            closed.append({"number": pr["number"], "app_id": app_id,
                            "pr_version": pr_version, "master_version": master_version})

    return closed


def main() -> int:
    token = os.environ["GH_TOKEN"]
    repo = os.environ.get("GH_REPOSITORY", "tekflox/aw-marketplace")
    closed = close_stale_syncs(token, repo)
    for c in closed:
        print(f"closed PR #{c['number']} ({c['app_id']}): "
              f"master already at {c['master_version']}, PR was {c['pr_version']}")
    if not closed:
        print("no stale sync PRs found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
