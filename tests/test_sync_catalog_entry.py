"""Unit tests for scripts/sync_catalog_entry.py.
Run with: .venv/aw/bin/python -m pytest repos/aw-marketplace/tests/test_sync_catalog_entry.py
"""
import copy
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from sync_catalog_entry import apply_to_catalog, create_entry, diff_entry  # noqa: E402

APP_MANIFEST = {
    "id": "essentials",
    "name": "Essential CLI Tools",
    "version": "0.2.0",
    "description": "Installs a set of essential CLI tools (now with docker).",
    "publisher": "TekFlox",
    "resource_estimate": {"cpu": "low", "memory": "-", "disk": "~80 MB"},
}

CATALOG_ENTRY = {
    "id": "essentials",
    "name": "Essential CLI Tools",
    "description": "Installs a set of essential CLI tools into the workspace.",
    "repo": "tekflox/aw-app-essentials",
    "ref": "master",
    "version": "0.1.0",
    "icon": "terminal",
    "category": "dev-tools",
    "tags": ["cli", "networking", "essentials", "docker"],
    "has_config": False,
    "bootstrap": True,
}


def test_diff_entry_detects_version_and_description_drift():
    changed, updated = diff_entry(APP_MANIFEST, CATALOG_ENTRY, new_ref="v0.2.0")
    assert changed is True
    assert updated["version"] == "0.2.0"
    assert updated["ref"] == "v0.2.0"
    assert updated["description"] == APP_MANIFEST["description"]
    # curated-only fields survive untouched
    assert updated["icon"] == "terminal"
    assert updated["category"] == "dev-tools"
    assert updated["bootstrap"] is True


def test_diff_entry_no_change_when_already_in_sync():
    entry = dict(CATALOG_ENTRY, version="0.2.0", ref="v0.2.0",
                  description=APP_MANIFEST["description"],
                  publisher=APP_MANIFEST["publisher"],
                  resource_estimate=APP_MANIFEST["resource_estimate"])
    changed, updated = diff_entry(APP_MANIFEST, entry, new_ref="v0.2.0")
    assert changed is False
    assert updated == entry


def test_diff_entry_does_not_mutate_inputs():
    manifest_copy = copy.deepcopy(APP_MANIFEST)
    entry_copy = copy.deepcopy(CATALOG_ENTRY)
    diff_entry(manifest_copy, entry_copy, new_ref="v0.2.0")
    assert manifest_copy == APP_MANIFEST
    assert entry_copy == CATALOG_ENTRY


def test_apply_to_catalog_updates_matching_app_only():
    catalog = {
        "manifest_version": 1,
        "apps": [
            {"id": "git", "name": "Git", "version": "0.1.0", "ref": "master"},
            dict(CATALOG_ENTRY),
        ],
    }
    changed, updated_catalog = apply_to_catalog(
        catalog, "essentials", APP_MANIFEST, new_ref="v0.2.0"
    )
    assert changed is True
    essentials = next(a for a in updated_catalog["apps"] if a["id"] == "essentials")
    assert essentials["version"] == "0.2.0"
    git_entry = next(a for a in updated_catalog["apps"] if a["id"] == "git")
    assert git_entry["version"] == "0.1.0"  # untouched


def test_create_entry_builds_conservative_first_listing():
    manifest = {
        "id": "mcp-tools",
        "name": "MCP Tools",
        "version": "0.2.0",
        "description": "Installs MCP helper tools.",
        "publisher": "TekFlox",
        "resource_estimate": {"cpu": "low", "memory": "low", "disk": "low"},
        "config_schema": {"type": "object", "properties": {"endpoint": {"type": "string"}}},
        "contributes": {
            "system_clis": [{"name": "aw-playwright-mcp", "installer": "scripts/install.sh"}]
        },
    }

    entry = create_entry(manifest, new_ref="v0.2.0", repo="tekflox/aw-app-mcp-tools")

    assert entry["id"] == "mcp-tools"
    assert entry["repo"] == "tekflox/aw-app-mcp-tools"
    assert entry["ref"] == "v0.2.0"
    assert entry["version"] == "0.2.0"
    assert entry["icon"] == "plug"
    assert entry["category"] == "dev-tools"
    assert entry["tags"] == ["mcp", "tools", "aw-playwright-mcp"]
    assert entry["has_config"] is True
    assert entry["bootstrap"] is True
    assert entry["publisher"] == "TekFlox"


def test_apply_to_catalog_adds_unknown_app_id():
    catalog = {"manifest_version": 1, "apps": [dict(CATALOG_ENTRY)]}
    manifest = dict(APP_MANIFEST, id="new-tool")

    changed, updated_catalog = apply_to_catalog(
        catalog, "new-tool", manifest, new_ref="v0.2.0", repo="tekflox/aw-app-new-tool"
    )

    assert changed is True
    new_entry = next(a for a in updated_catalog["apps"] if a["id"] == "new-tool")
    assert new_entry["repo"] == "tekflox/aw-app-new-tool"
