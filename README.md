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
