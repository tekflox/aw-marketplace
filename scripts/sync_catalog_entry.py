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
import sys

# Fields carried from aw-app.json into the apps.json entry when they differ.
# "version"/"ref" are handled separately (ref comes from the new tag, not
# aw-app.json, which has no ref field of its own).
SYNCED_FIELDS = ("name", "description", "publisher", "resource_estimate")


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


def apply_to_catalog(catalog, app_id, app_manifest, new_ref):
    """Find app_id in catalog['apps'] and diff/merge it in place.

    Returns (changed, catalog). Raises KeyError if app_id isn't in the
    catalog yet (new-app-onboarding is out of scope for this workflow —
    the marketplace entry must exist first).
    """
    for entry in catalog["apps"]:
        if entry["id"] == app_id:
            changed, updated = diff_entry(app_manifest, entry, new_ref)
            entry.clear()
            entry.update(updated)
            return changed, catalog
    raise KeyError(f"app id {app_id!r} not found in catalog")


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aw_app_json", help="Path to the app's aw-app.json")
    parser.add_argument("apps_json", help="Path to the marketplace's apps.json")
    parser.add_argument("new_ref", help="New pinned ref (e.g. v0.2.0)")
    parser.add_argument(
        "--write", action="store_true",
        help="Write the updated apps.json back in place. Without this, "
             "just reports whether a change is needed (exit 0=changed, 1=no-op).",
    )
    args = parser.parse_args(argv)

    app_manifest = json.loads(open(args.aw_app_json).read())
    catalog = json.loads(open(args.apps_json).read())

    changed, catalog = apply_to_catalog(
        catalog, app_manifest["id"], app_manifest, args.new_ref
    )

    if changed and args.write:
        with open(args.apps_json, "w") as f:
            json.dump(catalog, f, indent=2)
            f.write("\n")

    print("changed" if changed else "unchanged")
    return 0 if changed else 1


if __name__ == "__main__":
    sys.exit(_main())
