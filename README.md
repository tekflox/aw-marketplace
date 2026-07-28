# aw-marketplace

The **apps marketplace catalog** — a single `apps.json` listing every app
installable from the aw-workspace "Marketplace" screen (Apps view →
Marketplace button). JSON (not YAML) to stay field-name-consistent with the
apps' own `aw-app.json` manifest. This repo is the distribution SOURCE for the
[Decoupled Apps Framework ADR](../../docs/knowledge_base/docs/architecture/decoupled-apps-framework.md),
not the runtime that installs apps — the runtime lives in `aw-workspace`
(Phase 8 of the ADR's phased plan).

This repo holds **apps**, not agents/flows. There is a separate
[`agents-platform-marketplace`](../agents-platform-marketplace) repo for the
Agents Platform's agent/flow template catalog — different domain, different
consumer, don't conflate them.

## How it's consumed

1. User clicks **Apps → Marketplace** in the AW UI.
2. aw-workspace fetches this repo's `apps.json` (git-URL-backed catalog —
   feeds ADR Decision 5's `apps_catalog_cache` and the "Install My Apps"
   flow) and renders one card per `apps[]` entry (name, description, icon,
   tags) with an **Install** button.
3. **Install** pulls the app's own repo (`repo` @ `ref`), reads its
   `aw-app.json` manifest (the authoritative source of truth for
   permissions/contributes/config_schema — this catalog only carries a UX
   summary), runs the app's bootstrap/install hook if `bootstrap: true`
   (system CLIs, etc. — see the app's own `aw-app.json` `contributes`), then
   activates it per the ADR's Tier-1/Tier-2 runtime.
4. If the installed app's catalog entry has `has_config: true`, the UI opens
   that app's config/settings window right after install (the window itself
   is declared in the app's own manifest, e.g. `contributes.windows` /
   `contributes.settings_panels`).

This repo IS the git catalog that `feature:apps-marketplace-tab-git-catalog`
(the Marketplace tab in the Apps view) consumes, and it feeds ADR F8
(marketplace type) — see "Phase 8" in the Decoupled Apps Framework ADR.

## Files

- `apps.json` — the catalog. See [SCHEMA.md](SCHEMA.md) for the field
  reference.
- `schemas/apps.schema.json` — JSON Schema `apps.json` validates against.
- `tests/validate_apps.py` — validates `apps.json` against the schema +
  checks for duplicate `id`s: `.venv/aw/bin/python tests/validate_apps.py`.
- `.github/workflows/app-release.yml` — reusable release workflow (see
  "Marketplace auto-sync" below).
- `scripts/bump_version.py` / `scripts/sync_catalog_entry.py` — pure-function
  logic behind the reusable workflow, unit-tested in `tests/`.

## Marketplace auto-sync (App Update Mechanism ADR, Metade A)

Each `aw-app-*` repo has a ~10-line caller workflow
(`.github/workflows/release.yml`) that calls this repo's reusable
`app-release.yml` via `uses: tekflox/aw-marketplace/.github/workflows/app-release.yml@main`
+ `secrets: inherit`. Bumping the reusable workflow here propagates to every
caller's next run — no per-repo edits needed. On push to the app's default
branch it: bumps semver in `aw-app.json` (minor default, patch if every
commit since the last tag is `fix:`/`docs:`/`chore:`, major only via
`workflow_dispatch(bump=major)` or a `[major]` marker), commits with
`[skip release]` (anti-loop guard), tags `vX.Y.Z` + branches `release/vX.Y.Z`,
then opens/updates an idempotent PR here (`sync/<app-id>`) bumping the app's
`apps.json` entry (`version` + `ref` pinned to the new tag, plus
name/description/publisher/resource_estimate drift) — and auto-merges it
(`gh pr merge --auto --squash`) when the source repo is first-party
(`tekflox/*`).

**Setup required (one-time, human):** an org secret
`MARKETPLACE_SYNC_TOKEN` (a GitHub PAT, `repo` scope, on the `tekflox` org)
must exist so the workflow can push/PR into this repo from the caller repos.
It does **not** exist yet as of 2026-07-28 — until it's created, pushes to
apps with the caller workflow installed will fail at the "Checkout
aw-marketplace scripts + catalog" / bump-and-push step with an auth error.
See the [App Update Mechanism ADR](../../docs/knowledge_base/docs/architecture/app-update-mechanism.md).
Branch protection on `master` requiring the `Validate / validate-apps-json`
check (from `.github/workflows/validate.yml`) is also not yet configured —
needed for the "required check" half of the auto-merge story.

## Seeded apps

- **git** ([aw-app-git](../aw-app-git)) — installs `git` + GitHub CLI
  (`gh`); `has_config: true` (gh login panel).
- **essentials** ([aw-app-essentials](../aw-app-essentials)) — installs
  `telnet`/`ping`/`curl`/`nc`/`perl`/`python`; `has_config: false` (no
  settings, pure command install).

## Testing done

```
$ .venv/aw/bin/python tests/validate_apps.py
OK: apps.json is valid (2 apps: git, essentials)
```
