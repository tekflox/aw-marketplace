"""validate_apps.py validates whichever catalog it is pointed at.

The path argument is what lets app-release.yml's `catalog_repo` input work:
a private app syncs into tekflox/aw-marketplace-private, which carries only
an apps.json — the schema still comes from this repo.
"""
import json
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

import validate_apps  # noqa: E402


def write_catalog(tmp_path, apps):
    path = tmp_path / "apps.json"
    path.write_text(json.dumps({"manifest_version": 1, "apps": apps}))
    return path


def an_app(app_id="crispal"):
    return {
        "id": app_id,
        "name": "Crispal",
        "description": "The Crispal stack.",
        "repo": "tekflox/aw-app-crispal",
        "has_config": True,
        "bootstrap": False,
        "signed": True,
        "resource_estimate": {"cpu": "low", "memory": "~1 GB", "disk": "~30 GB"},
    }


def test_no_argument_validates_this_repos_own_catalog(capsys):
    assert validate_apps.main([]) == 0
    assert str(ROOT / "apps.json") in capsys.readouterr().out


def test_an_external_catalog_is_validated_against_this_repos_schema(tmp_path, capsys):
    path = write_catalog(tmp_path, [an_app()])
    assert validate_apps.main([str(path)]) == 0
    assert "1 apps: crispal" in capsys.readouterr().out


def test_a_schema_violation_in_an_external_catalog_still_fails(tmp_path):
    bad = an_app()
    bad["resource_estimate"] = {"cpu": "enormous", "memory": "-", "disk": "-"}
    path = write_catalog(tmp_path, [bad])
    with pytest.raises(jsonschema.ValidationError):
        validate_apps.main([str(path)])


def test_duplicate_ids_in_an_external_catalog_fail(tmp_path):
    path = write_catalog(tmp_path, [an_app(), an_app()])
    assert validate_apps.main([str(path)]) == 1


def test_a_missing_catalog_fails_instead_of_raising(tmp_path):
    """A typo'd path must not read as "nothing to validate, all good"."""
    assert validate_apps.main([str(tmp_path / "nope.json")]) == 1


def test_more_than_one_path_is_a_usage_error(tmp_path):
    path = write_catalog(tmp_path, [an_app()])
    assert validate_apps.main([str(path), str(path)]) == 2
