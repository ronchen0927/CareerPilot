# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
cd backend
uv sync --group dev                               # Install dependencies (incl. dev tools)
uv run uvicorn app.main:app --reload --port 8000  # Start API server (dev)
uv run pytest                                     # Run all tests
uv run pytest tests/test_scraper.py -v            # Run a single test file
uv run ruff check .                               # Lint (finds unused imports, style issues)
uv run ruff format .                              # Format (whitespace/line-length only)
uv run pre-commit install                         # Install git hooks (run once)
```

> `ruff check` and `ruff format` do different things — always run both. CI runs both.

Settings can be overridden via a `backend/.env` file (uses `pydantic-settings`).

### Frontend

```bash
cd frontend
python -m http.server 3000   # Serve at http://localhost:3000
```

The frontend hardcodes `API_BASE = "http://localhost:8000"` in `frontend/js/app.js`.

## Architecture

```
backend/
  app/
    main.py         # FastAPI app: CORS, static files, lifespan (starts scheduler task)
    config.py       # Settings (pydantic-settings), AREA_OPTIONS, EXPERIENCE_OPTIONS constants
    models.py       # Pydantic models: JobSearchRequest, JobListing, AlertCreateRequest, etc.
    scraper.py      # Async scraper hitting 104's internal JSON API via aiohttp
    alerts.py       # load_alerts() / save_alerts() — persists to backend/alerts.json
    scheduler.py    # Background asyncio loop: checks due alerts, scrapes, notifies
    routers/
      jobs.py       # POST /api/jobs/search, GET /api/jobs/options
      alerts.py     # GET/POST /api/alerts, DELETE /api/alerts/{id}, POST /{id}/trigger
  tests/
    conftest.py     # Fixtures: tmp_alerts_file (monkeypatches ALERTS_FILE), client (TestClient)
    test_scraper.py
    test_scheduler.py
    test_alerts_storage.py
    test_api_jobs.py
    test_api_alerts.py
frontend/
  index.html        # Main search page + bookmarks list
  dashboard.html    # Kanban board (drag-and-drop job status tracking)
  alerts.html       # Scheduled alert management UI
  js/
    utils.js        # Shared helper: escapeHtml()
    app.js          # Search, salary filter, job modal, bookmarks, CSV export
    dashboard.js    # Kanban board with HTML5 Drag and Drop API
    alerts.js       # Alert CRUD UI, Line Notify / Webhook toggle
static/             # Served at /static by FastAPI
```

**Data flow:** Frontend form → `POST /api/jobs/search` → `scraper.scrape_jobs()` fetches all pages concurrently via `asyncio.gather` → deduplicates by job link → sorts by date descending → returns `JobSearchResponse`.

**104 API:** Targets `https://www.104.com.tw/jobs/search/api/jobs` with a `Referer` header and SSL cert verification disabled (104 cert quirk). Area and experience codes are URL-encoded comma-joined lists.

**Scheduler:** Runs as an asyncio task inside the FastAPI `lifespan` context manager (no external dependency). Wakes every 60 seconds, checks each alert's `interval_minutes` against `last_run`, scrapes if due, sends Line Notify or Webhook, updates `seen_links` and `last_run` in `alerts.json`.

**Frontend state:** Bookmarks and kanban status stored in `localStorage`. `utils.js` is loaded before each page's own script and provides the shared `escapeHtml()` function.

## Testing approach

- Pure-function unit tests (scraper helpers, `_is_due`) need no mocking.
- API tests use `TestClient` with `scrape_jobs` mocked via `AsyncMock` and `ALERTS_FILE` redirected to a `tmp_path` via `monkeypatch` — no real network, no real files left behind.
- `run_scheduler` is replaced with `AsyncMock` in the `client` fixture so the lifespan completes instantly.
- When patching functions that are imported lazily inside a function body (e.g. `_fetch_new_jobs` in `trigger_alert`), patch the source module (`app.scheduler`) not the importing module (`app.routers.alerts`).
