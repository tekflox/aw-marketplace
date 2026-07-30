#!/usr/bin/env python3
"""Diff an app's aw-app.json against its apps.json catalog entry and merge
in the fields that impact the marketplace (version, ref, name, description,
publisher, resource_estimate). Pure functions — no git/gh/network calls —
so this is unit-testable; see tests/test_sync_catalog_entry.py.

CLI mode is called from .github/workflows/app-release.yml with the app's
aw-app.json, the marketplace's apps.json, and the freshly-cut release tag.
"""
import argparse
import json
import os
import sys

# Fields carried from aw-app.json into the apps.json entry when they differ.
# "version"/"ref" are handled separately (ref comes from the new tag, not
# aw-app.json, which has no ref field of its own).
SYNCED_FIELDS = ("name", "description", "publisher", "resource_estimate")


def _tags_for_manifest(app_manifest):
    tags = []
    for part in app_manifest["id"].split("-"):
        if part and part not in tags:
            tags.append(part)
    for cli in app_manifest.get("contributes", {}).get("system_clis", []):
        name = cli.get("name")
        if name and name not in tags:
            tags.append(name)
    return tags


def create_entry(app_manifest, new_ref, repo=None):
    """Create a first catalog entry for a new app manifest."""
    contributes = app_manifest.get("contributes", {})
    config_properties = app_manifest.get("config_schema", {}).get("properties") or {}
    app_id = app_manifest["id"]
    entry = {
        "id": app_id,
        "name": app_manifest["name"],
        "description": app_manifest["description"],
        "repo": repo or os.environ.get("APP_REPO") or f"tekflox/aw-app-{app_id}",
        "ref": new_ref,
        "version": app_manifest["version"],
        "icon": "plug",
        "category": "dev-tools",
        "tags": _tags_for_manifest(app_manifest),
        "has_config": bool(config_properties),
        "bootstrap": bool(contributes.get("system_clis")),
    }
    for field in ("publisher", "resource_estimate"):
        if field in app_manifest:
            entry[field] = app_manifest[field]
    return entry


def diff_entry(app_manifest, catalog_entry, new_ref):
    """Return (changed, updated_entry). Never mutates the inputs."""
    updated = dict(catalog_entry)
    changed = False

    new_version = app_manifest.get("version")
    if new_version and updated.get("version") != new_version:
        updated["version"] = new_version
        changed = True

    if new_ref and updated.get("ref") != new_ref:
        updated["ref"] = new_ref
        changed = True

    for field in SYNCED_FIELDS:
        if field not in app_manifest:
            continue
        if updated.get(field) != app_manifest[field]:
            updated[field] = app_manifest[field]
            changed = True

    return changed, updated


def apply_to_catalog(catalog, app_id, app_manifest, new_ref, repo=None):
    """Find app_id in catalog['apps'] and diff/merge it in place.

    Returns (changed, catalog). If app_id is not present yet, appends a
    conservative first catalog entry so a new aw-app-* repo's first release
    can open the marketplace sync PR automatically.
    """
    for entry in catalog["apps"]:
        if entry["id"] == app_id:
            changed, updated = diff_entry(app_manifest, entry, new_ref)
            entry.clear()
            entry.update(updated)
            return changed, catalog
    catalog["apps"].append(create_entry(app_manifest, new_ref, repo=repo))
    return True, catalog


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aw_app_json", help="Path to the app's aw-app.json")
    parser.add_argument("apps_json", help="Path to the marketplace's apps.json")
    parser.add_argument("new_ref", help="New pinned ref (e.g. v0.2.0)")
    parser.add_argument(
        "--repo",
        default=None,
        help="Source repository for a new catalog entry. Defaults to APP_REPO, "
             "then tekflox/aw-app-<id>.",
    )
    parser.add_argument(
        "--write", action="store_true",
        help="Write the updated apps.json back in place. Without this, "
             "just reports whether a change is needed (exit 0=changed, 1=no-op).",
    )
    args = parser.parse_args(argv)

    app_manifest = json.loads(open(args.aw_app_json).read())
    catalog = json.loads(open(args.apps_json).read())

    changed, catalog = apply_to_catalog(
        catalog, app_manifest["id"], app_manifest, args.new_ref, repo=args.repo
    )

    if changed and args.write:
        with open(args.apps_json, "w") as f:
            json.dump(catalog, f, indent=2)
            f.write("\n")

    print("changed" if changed else "unchanged")
    return 0 if changed else 1


if __name__ == "__main__":
    sys.exit(_main())
