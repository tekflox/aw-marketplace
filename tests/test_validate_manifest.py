"""validate_manifest.py's declarative-widget vocabulary check.

The script runs its checks as module-level code (sys.exit on failure), so it
is exercised as a subprocess against a throwaway manifest + window spec
rather than imported.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VALIDATE = ROOT / "scripts" / "validate_manifest.py"
SCHEMA = ROOT / "schemas" / "aw-app.schema.json"


def make_app(tmp_path, window_spec_widgets):
    spec_path = tmp_path / "window.json"
    spec_path.write_text(json.dumps({
        "regions": [{"id": "main", "widgets": window_spec_widgets}],
    }))
    manifest = {
        "manifest_version": 1,
        "id": "fixture-app",
        "name": "Fixture App",
        "version": "0.1.0",
        "tier": "inprocess",
        "runtime": {"python": ">=3.11", "entrypoint": "fixture:Plugin"},
        "permissions": [],
        "contributes": {
            "windows": [
                {"id": "fixture-app.main", "title": "Fixture",
                 "body": {"type": "declarative", "spec": "window.json"}},
            ],
        },
    }
    manifest_path = tmp_path / "aw-app.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path


def run_validate(manifest_path):
    return subprocess.run(
        [sys.executable, str(VALIDATE), str(manifest_path), "--schema", str(SCHEMA)],
        capture_output=True, text=True,
    )


def test_toggle_widget_is_accepted(tmp_path):
    manifest_path = make_app(tmp_path, [{
        "type": "toggle",
        "bind": "GET /api/apps/fixture-app/leaf-tool/proxy_status",
        "field": "enabled",
        "action": {"call": "POST /api/apps/fixture-app/leaf-tool/proxy_set"},
        "label": "Route through proxy",
        "offline_field": "offline",
        "offline_text": "Start the container to change this setting.",
    }])
    result = run_validate(manifest_path)
    assert result.returncode == 0, result.stderr


def test_unknown_widget_still_fails(tmp_path):
    manifest_path = make_app(tmp_path, [{"type": "not_a_real_widget"}])
    result = run_validate(manifest_path)
    assert result.returncode == 1
    assert "not_a_real_widget" in result.stderr


def make_knowledge_app(tmp_path, knowledge_path):
    manifest = {
        "manifest_version": 1,
        "id": "fixture-app",
        "name": "Fixture App",
        "version": "0.1.0",
        "tier": "inprocess",
        "runtime": {"python": ">=3.11", "entrypoint": "fixture:Plugin"},
        "permissions": [],
        "contributes": {
            "knowledge": {"path": knowledge_path},
        },
    }
    manifest_path = tmp_path / "aw-app.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path


def test_knowledge_path_that_exists_as_a_directory_passes(tmp_path):
    (tmp_path / "docs").mkdir()
    manifest_path = make_knowledge_app(tmp_path, "docs")
    result = run_validate(manifest_path)
    assert result.returncode == 0, result.stderr


def test_knowledge_path_that_is_missing_fails_naming_the_path(tmp_path):
    manifest_path = make_knowledge_app(tmp_path, "docs")
    result = run_validate(manifest_path)
    assert result.returncode == 1
    assert "docs" in result.stderr
