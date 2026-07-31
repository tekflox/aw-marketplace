import copy
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schemas" / "apps.schema.json").read_text())


def make_catalog(resource_estimate):
    return {
        "manifest_version": 1,
        "apps": [
            {
                "id": "browser",
                "name": "AW Browser",
                "description": "Browser app",
                "repo": "tekflox/aw-app-browser",
                "has_config": True,
                "bootstrap": False,
                "signed": True,
                "resource_estimate": resource_estimate,
            }
        ],
    }


def validate(resource_estimate):
    jsonschema.validate(
        instance=make_catalog(copy.deepcopy(resource_estimate)),
        schema=SCHEMA,
    )


def test_resource_estimate_accepts_categories_and_human_sizes():
    validate({"cpu": "medium", "memory": "low", "disk": "high"})
    validate({"cpu": "medium", "memory": "~500 MB", "disk": "1 GB"})
    validate({"cpu": "medium", "memory": "256MB", "disk": "~1.5 GB"})


def test_resource_estimate_rejects_explanatory_suffixes():
    with pytest.raises(jsonschema.ValidationError):
        validate({"cpu": "medium", "memory": "~500 MB", "disk": "~500 MB (prebuilt image)"})
