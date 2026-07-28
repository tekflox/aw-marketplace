"""Unit tests for scripts/bump_version.py.
Run with: .venv/aw/bin/python -m pytest repos/aw-marketplace/tests/test_bump_version.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from bump_version import bump_semver, determine_bump  # noqa: E402


def test_determine_bump_defaults_to_minor_with_no_commits():
    assert determine_bump([]) == "minor"


def test_determine_bump_defaults_to_minor_for_feat_commit():
    assert determine_bump(["feat: add docker CLI"]) == "minor"


def test_determine_bump_patch_when_all_commits_are_fix_docs_chore():
    assert determine_bump(["fix: symlink docker.sock", "chore: bump readme"]) == "patch"
    assert determine_bump(["docs: refresh description"]) == "patch"


def test_determine_bump_minor_when_mixed_with_non_conventional():
    assert determine_bump(["fix: a", "add random feature"]) == "minor"


def test_determine_bump_manual_major_wins_over_everything():
    assert determine_bump(["fix: a", "docs: b"], manual_bump="major") == "major"


def test_bump_semver_patch():
    assert bump_semver("0.1.0", "patch") == "0.1.1"


def test_bump_semver_minor_resets_patch():
    assert bump_semver("0.1.5", "minor") == "0.2.0"


def test_bump_semver_major_resets_minor_and_patch():
    assert bump_semver("1.4.9", "major") == "2.0.0"


def test_bump_semver_rejects_non_semver():
    import pytest

    with pytest.raises(ValueError):
        bump_semver("not-a-version", "minor")
