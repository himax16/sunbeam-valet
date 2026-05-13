# Bug Triage Dashboard

Starlette-based web dashboard for triaging bugs and syncing from watchtower.

## Usage

```sh
uv run sunbeam_valet dashboard
```

Opens at **<http://127.0.0.1:8473>**.

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--port`, `-p` | `8473` | Port to bind |
| `--host` | `127.0.0.1` | Host interface |

## Architecture

| Module | Purpose |
|--------|---------|
| `app.py` | Starlette app: routes, request handlers, server startup |
| `models.py` | Pydantic `Bug` model |
| `store.py` | In-memory bug store backed by SQLite; refreshed after each sync |
| `db.py` | SQLite cache (`~/.cache/sunbeam-valet/cache.db`) |
| `settings.py` | JSON settings (`~/.config/sunbeam-valet/dashboard_settings.json`) |
| `watchtower.py` | Watchtower server lifecycle and bug sync |
| `judge.py` | LLM AI judge agent (pydantic-ai) |
| `templates/` | Jinja2 HTML templates |
| `static/style.css` | Pragma-inspired CSS with design tokens and light/dark theme |

## Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Main dashboard with bug table, toolbar, sync button |
| GET | `/bug/{id}` | Full-page bug detail with judge history |
| POST | `/bug/{id}/triage` | Auto-triage a bug |
| POST | `/bug/{id}/judge` | **AI judge** — runs LLM agent, saves verdict to SQLite |
| POST | `/bug/add` | Add a bug manually |
| GET | `/config` | Watchtower settings page |
| POST | `/config/save` | Save settings |
| POST | `/api/sync` | Sync bugs from watchtower (clears and replaces cache) |
| GET | `/api/sync/status` | Last sync status and bug count (JSON) |

## Watchtower Integration

1. Go to **Settings** and configure the watchtower server address and config path
2. Click **Sync from Watchtower** — the dashboard will:
   - Start a watchtower server if needed (with `--config` pointing to the configured YAML)
   - Trigger `POST /api/v1/cache/sync/bugs`
   - Fetch bugs from `GET /api/v1/bugs`
   - **Clear and replace** all bugs in SQLite

### Settings

| Field | Default | Description |
|-------|---------|-------------|
| `watchtower_server_address` | `http://127.0.0.1:8472` | Watchtower API URL |
| `watchtower_server_host` | `127.0.0.1` | Host for auto-started server |
| `watchtower_server_port` | `8472` | Port for auto-started server |
| `watchtower_config_path` | `~/.config/sunbeam-watchtower/config.yaml` | Config passed via `--config` |
| `watchtower_token` | `""` | Optional bearer token |
| `watchtower_use_daemon` | `false` | Use `watchtower server start` |

## SQLite Schema

| Table | Purpose |
|-------|---------|
| `bugs` | Cached bugs from watchtower (replaced on each sync) |
| `sync_log` | Sync timestamps and status |
| `judgements` | AI judge results (verdict, confidence, summary, concerns) |

## AI Judge

The **Judge** button on a triaged bug runs a `pydantic-ai` agent that:

- Analyzes the bug title, description, and source
- Returns: verdict (critical/high/medium/low/wontfix/invalid), confidence, summary, concerns
- Saves the result to the `judgements` table
- Falls back to a heuristic demo judge if no AI model is available
- Sets the bug status to `accepted` with the verdict-derived priority

## Workflow

1. **Sync** bugs from watchtower (replaces local cache)
2. Click bug title → detail page
3. Click **Triage** → auto-classification
4. Click **Judge** → AI agent evaluates and saves verdict
5. View judgement history on the detail page

## Theme

Toggle light/dark via ◐ button. Persists in localStorage and respects `prefers-color-scheme`. Based on Canonical Pragma design tokens.
