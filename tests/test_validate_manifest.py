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


def make_indexing_app(tmp_path, indexing_entries):
    manifest = {
        "manifest_version": 1,
        "id": "fixture-app",
        "name": "Fixture App",
        "version": "0.1.0",
        "tier": "inprocess",
        "runtime": {"python": ">=3.11", "entrypoint": "fixture:Plugin"},
        "permissions": [],
        "contributes": {
            "mcp": {"indexing": indexing_entries},
        },
    }
    manifest_path = tmp_path / "aw-app.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path


def test_mcp_indexing_not_declared_still_validates(tmp_path):
    # Every app installed today has no 'indexing' key at all.
    manifest_path = tmp_path / "aw-app.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": 1,
        "id": "fixture-app",
        "name": "Fixture App",
        "version": "0.1.0",
        "tier": "inprocess",
        "runtime": {"python": ">=3.11", "entrypoint": "fixture:Plugin"},
        "permissions": [],
        "contributes": {},
    }))
    result = run_validate(manifest_path)
    assert result.returncode == 0, result.stderr


def test_mcp_indexing_well_formed_restriction_passes(tmp_path):
    manifest_path = make_indexing_app(tmp_path, [
        {"tool": "search_graph", "call": False, "output": True,
         "reason": "arguments carry a free-text query that may include PII"},
    ])
    result = run_validate(manifest_path)
    assert result.returncode == 0, result.stderr


def test_mcp_indexing_restriction_missing_reason_fails(tmp_path):
    manifest_path = make_indexing_app(tmp_path, [
        {"tool": "search_graph", "call": False, "output": True},
    ])
    result = run_validate(manifest_path)
    assert result.returncode == 1
    assert "reason" in result.stderr


def test_mcp_indexing_floor_tool_declared_indexable_fails(tmp_path):
    manifest_path = make_indexing_app(tmp_path, [
        {"tool": "write_secret", "call": True, "output": False,
         "reason": "trying to lift the floor"},
    ])
    result = run_validate(manifest_path)
    assert result.returncode == 1
    assert "hard floor" in result.stderr


def test_mcp_indexing_floor_tool_both_axes_false_passes(tmp_path):
    manifest_path = make_indexing_app(tmp_path, [
        {"tool": "write_secret", "call": False, "output": False,
         "reason": "redundant under the floor"},
    ])
    result = run_validate(manifest_path)
    assert result.returncode == 0, result.stderr


def test_mcp_indexing_gateway_prefixed_tool_name_fails(tmp_path):
    manifest_path = make_indexing_app(tmp_path, [
        {"tool": "mcp__aw-gateway__aw__aw_secrets__write_secret",
         "call": False, "output": False, "reason": "x"},
    ])
    result = run_validate(manifest_path)
    assert result.returncode == 1
    assert "bare terminal segment" in result.stderr


def test_mcp_indexing_duplicate_tool_fails(tmp_path):
    manifest_path = make_indexing_app(tmp_path, [
        {"tool": "search_graph", "call": True, "output": True},
        {"tool": "search_graph", "call": False, "output": False, "reason": "x"},
    ])
    result = run_validate(manifest_path)
    assert result.returncode == 1
    assert "more than once" in result.stderr


def test_mcp_indexing_entry_missing_required_schema_keys_fails(tmp_path):
    # The JSON schema itself enforces tool/call/output presence and types.
    manifest_path = make_indexing_app(tmp_path, [{"tool": "search_graph", "call": True}])
    result = run_validate(manifest_path)
    assert result.returncode == 1
