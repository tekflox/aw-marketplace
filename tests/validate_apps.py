#!/usr/bin/env python3
"""Validates apps.json against schemas/apps.schema.json and checks that
every `id` is unique. Run with the AW venv (jsonschema is installed
there): .venv/aw/bin/python tests/validate_apps.py
"""
import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent

catalog = json.loads((ROOT / "apps.json").read_text())
schema = json.loads((ROOT / "schemas" / "apps.schema.json").read_text())

jsonschema.validate(instance=catalog, schema=schema)

ids = [app["id"] for app in catalog["apps"]]
if len(ids) != len(set(ids)):
    print(f"FAIL: duplicate app ids in apps.json: {ids}", file=sys.stderr)
    sys.exit(1)

print(f"OK: apps.json is valid ({len(ids)} apps: {', '.join(ids)})")
