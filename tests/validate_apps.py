#!/usr/bin/env python3
"""Validates a catalog's apps.json against schemas/apps.schema.json and
checks that every `id` is unique.

    .venv/aw/bin/python tests/validate_apps.py                  # this repo
    .venv/aw/bin/python tests/validate_apps.py ../_catalog/apps.json

The optional path exists because the catalog being released into is no
longer always this repo: app-release.yml takes a `catalog_repo` input, so a
private app syncs into tekflox/aw-marketplace-private instead. The **schema**
still always comes from this repo — a private catalog carries only its
apps.json, and there is no reason for it to fork the schema.
"""
import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        print(f"usage: {Path(sys.argv[0]).name} [apps.json]", file=sys.stderr)
        return 2
    catalog_path = Path(argv[0]).resolve() if argv else ROOT / "apps.json"
    if not catalog_path.is_file():
        print(f"FAIL: no catalog at {catalog_path}", file=sys.stderr)
        return 1

    catalog = json.loads(catalog_path.read_text())
    schema = json.loads((ROOT / "schemas" / "apps.schema.json").read_text())

    jsonschema.validate(instance=catalog, schema=schema)

    ids = [app["id"] for app in catalog["apps"]]
    if len(ids) != len(set(ids)):
        print(f"FAIL: duplicate app ids in {catalog_path}: {ids}", file=sys.stderr)
        return 1

    print(f"OK: {catalog_path} is valid ({len(ids)} apps: {', '.join(ids)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
