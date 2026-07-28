# apps.json schema

JSON — kept field-name-consistent with the apps' own `aw-app.json` manifest
(`manifest_version`, `id`, `name`, `description`, `version`; see the
[Decoupled Apps Framework ADR](../../docs/knowledge_base/docs/architecture/decoupled-apps-framework.md)).
Structural schema lives in `schemas/apps.schema.json`; validated by
`tests/validate_apps.py`.

```json
{
  "manifest_version": 1,
  "apps": [
    {
      "id": "git",
      "name": "Git + GitHub CLI",
      "description": "Installs git and the GitHub CLI...",
      "repo": "tekflox/aw-app-git",
      "ref": "main",
      "version": "0.1.0",
      "icon": "git-branch",
      "category": "dev-tools",
      "tags": ["git", "github", "cli"],
      "has_config": true,
      "bootstrap": true
    }
  ]
}
```

## Fields

| Field | Required | Type | Meaning |
|---|---|---|---|
| `manifest_version` | yes (top-level) | integer | Catalog format version — bump on breaking field changes. |
| `id` | yes | string, `^[a-z][a-z0-9-]{1,40}$` | Must match the app's own `aw-app.json` manifest `id` — this is the namespace key everywhere downstream (routes, tables, commands — see the ADR's Decision 8). |
| `name` | yes | string | Display name in the Marketplace list. |
| `description` | yes | string | Shown under the name in the Marketplace list. |
| `repo` | yes | string | Where the app's code + `aw-app.json` live — a repo path (`owner/name`, resolved against GitHub) or a full git URL. |
| `ref` | no | string | Tag/branch/commit to pin the install to. Defaults to the repo's default branch when omitted. |
| `version` | no | string (semver) | Optional pin, matched against the installed `aw-app.json`'s own `version` field — a mismatch is a signal the catalog is stale, not necessarily a hard block. |
| `icon` | no | string | Icon identifier for the Marketplace card. |
| `category` | no | string | Grouping/filter in the Marketplace UI (e.g. `dev-tools`). |
| `tags` | no | list of strings | Search/filter tags. |
| `has_config` | yes | bool | Whether the app has a config/settings window to open once install finishes. `aw-app-git` = `true` (gh login panel); `aw-app-essentials` = `false` (no settings — pure command install). |
| `bootstrap` | yes | bool | Whether installing this app runs a bootstrap/install hook (e.g. apt-installs system CLIs). Both seeded apps = `true`. |
| `publisher` | no | string | Marketplace display attribution. Not authored here — the workspace's catalog endpoint (`GET /api/apps/-/catalog`) fetches the app's own `aw-app.json` and merges its `publisher` field in at serve time (default `"TekFlox"`). Set it here only to override that value without touching the app repo. |
| `resource_estimate` | no | object `{cpu, memory, disk}`, each `"low"\|"medium"\|"high"` | Same deal as `publisher` — normally sourced from the app's `aw-app.json resource_estimate` field and merged in server-side; set here only to override. |
| `what_you_get` | no | object `{mcp_tools, ui_screens, commands}` (lists of strings) | Always server-derived, never authored here — the catalog endpoint computes it from the app's `aw-app.json contributes` (MCP tools from `contributes.mcp.provides`, UI screens from `contributes.windows`/`contributes.nav`, commands from `contributes.system_clis`/`contributes.commands`). Present only when the manifest fetch succeeds; omitted otherwise. |

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

After editing `apps.json`:

```bash
.venv/aw/bin/python tests/validate_apps.py
```

Checks: parses as valid JSON, matches `schemas/apps.schema.json`, no
duplicate `id`s.
