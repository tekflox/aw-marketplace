# apps.yaml schema

YAML (not JSON) — this file is meant to be hand-edited by Frederico when
adding/curating marketplace apps. Structural schema lives in
`schemas/apps.schema.json`; validated by `tests/validate_apps.py`.

```yaml
version: 1            # catalog format version — bump on breaking field changes

apps:
  - id: git            # required. matches the app's own aw-app.json `id`
    name: Git + GitHub CLI       # required. shown in the Marketplace list
    description: >-              # required. shown in the Marketplace list
      Installs git and the GitHub CLI...
    repo: tekflox/aw-app-git      # required. repo path (owner/name) or full git URL
                                    # where the app's code + aw-app.json live
    ref: main                     # optional. tag/branch/commit to pin install to
    version: 0.1.0                 # optional. semver pin, matched against the
                                    # app's own aw-app.json `version`
    icon: git-branch               # optional. icon name shown in the Marketplace list
    category: dev-tools            # optional. grouping in the Marketplace UI
    tags: [git, github, cli]       # optional. filter/search tags
    has_config: true               # required. whether the app has a config/settings
                                    # window to open right after install
    bootstrap: true                # required. whether installing this app runs a
                                    # bootstrap/install hook (e.g. system CLIs)
```

## Fields

| Field | Required | Type | Meaning |
|---|---|---|---|
| `id` | yes | string, `^[a-z][a-z0-9-]{1,40}$` | Must match the app's own `aw-app.json` manifest `id` — this is the namespace key everywhere downstream (routes, tables, commands — see the ADR's Decision 8). |
| `name` | yes | string | Display name in the Marketplace list. |
| `description` | yes | string | Shown under the name in the Marketplace list. |
| `repo` | yes | string | Where the app's code + `aw-app.json` live — a repo path (`owner/name`, resolved against GitHub) or a full git URL. |
| `ref` | no | string | Tag/branch/commit to pin the install to. Defaults to the repo's default branch when omitted. |
| `version` | no | string (semver) | Optional pin, cross-checked against the installed `aw-app.json`'s own `version` — a mismatch is a signal the catalog is stale, not necessarily a hard block. |
| `icon` | no | string | Icon identifier for the Marketplace card. |
| `category` | no | string | Grouping/filter in the Marketplace UI (e.g. `dev-tools`). |
| `tags` | no | list of strings | Search/filter tags. |
| `has_config` | yes | bool | Whether the app has a config/settings window to open once install finishes. `aw-app-git` = `true` (gh login panel); `aw-app-essentials` = `false` (no settings — pure command install). |
| `bootstrap` | yes | bool | Whether installing this app runs a bootstrap/install hook (e.g. apt-installs system CLIs). Both seeded apps = `true`. |

**Note:** the authoritative bootstrap/config declaration lives in the app's
own `aw-app.json` (`contributes.system_clis`, `contributes.settings_panels`,
`config_schema` — see the
[Decoupled Apps Framework ADR](../../docs/knowledge_base/docs/architecture/decoupled-apps-framework.md),
Decision 2). The `has_config`/`bootstrap` booleans here are a **summary for
the Marketplace list UX** ("does this app need a config step after
install?", "will this run something on my machine?") — not a duplicate
source of truth. If a catalog entry and the app's own manifest disagree,
the manifest wins at install time.

## How the catalog is consumed

See the "How it's consumed" section in [README.md](README.md) for the full
click → fetch → install → config-window flow.

## Validating changes

After editing `apps.yaml`:

```bash
.venv/aw/bin/python tests/validate_apps.py
```

Checks: parses as valid YAML, matches `schemas/apps.schema.json`, no
duplicate `id`s.
