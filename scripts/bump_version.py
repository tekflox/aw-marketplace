#!/usr/bin/env python3
"""Semver bump logic for the app-release reusable workflow.

Pure functions (no git/gh calls) so they're unit-testable in isolation —
see tests/test_bump_version.py. CLI mode is a thin wrapper called from
.github/workflows/app-release.yml.
"""
import argparse
import re
import sys

CONVENTIONAL_PATCH_PREFIXES = ("fix:", "docs:", "chore:")
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def determine_bump(commit_subjects, manual_bump=None):
    """Decide bump kind from commit subjects since the last tag.

    manual_bump (from workflow_dispatch input or a `[major]` marker in the
    triggering commit message) always wins. Otherwise: patch only if every
    commit is fix:/docs:/chore: (conventional-commit-lite); minor by default.
    """
    if manual_bump == "major":
        return "major"
    subjects = [s.strip() for s in commit_subjects if s.strip()]
    if subjects and all(
        any(s.startswith(p) for p in CONVENTIONAL_PATCH_PREFIXES) for s in subjects
    ):
        return "patch"
    return "minor"


def bump_semver(version, bump):
    match = SEMVER_RE.match(version.strip())
    if not match:
        raise ValueError(f"not a plain X.Y.Z semver: {version!r}")
    major, minor, patch = (int(part) for part in match.groups())
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown bump kind: {bump!r}")


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current_version")
    parser.add_argument(
        "--manual-bump", choices=["major"], default=None,
        help="Force major (workflow_dispatch bump=major or [major] marker).",
    )
    parser.add_argument(
        "--commit-subjects-file", default=None,
        help="Path to a file with one commit subject per line "
             "(git log --format=%%s since the last tag). Omit for no commits.",
    )
    args = parser.parse_args(argv)

    subjects = []
    if args.commit_subjects_file:
        with open(args.commit_subjects_file) as f:
            subjects = f.readlines()

    bump = determine_bump(subjects, manual_bump=args.manual_bump)
    new_version = bump_semver(args.current_version, bump)
    print(new_version)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
