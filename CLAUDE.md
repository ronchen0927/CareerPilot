# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
cd backend
uv sync --group dev                               # Install dependencies (incl. dev)
uv run uvicorn app.main:app --reload --port 8000  # Start API server (dev)
uv run pytest                                     # Run all tests
uv run pytest tests/test_scraper.py -v            # Run a single test file
```

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
    main.py       # FastAPI app setup: CORS, static files, router registration
    config.py     # Settings (pydantic-settings), AREA_OPTIONS, EXPERIENCE_OPTIONS constants
    models.py     # Pydantic models: JobSearchRequest, JobListing, JobSearchResponse
    scraper.py    # Async scraper hitting 104's internal JSON API via aiohttp
    routers/
      jobs.py     # /api/jobs/search (POST) and /api/jobs/options (GET)
frontend/
  index.html      # Single-page app shell
  css/style.css
  js/app.js       # Vanilla JS: fetches options on load, submits search, renders results table
static/           # Served at /static by FastAPI
```

**Data flow:** Frontend form → `POST /api/jobs/search` → `scraper.scrape_jobs()` fetches all pages concurrently via `asyncio.gather` → deduplicates by job link → sorts by date descending → returns `JobSearchResponse`.

**104 API:** The scraper targets `https://www.104.com.tw/jobs/search/api/jobs` with a `Referer` header and SSL cert verification disabled (104 cert quirk). Area and experience codes are URL-encoded comma-joined lists.

**Tests** live in `backend/tests/`. Pure-function unit tests need no network; API tests use `TestClient` with `scrape_jobs` mocked and `ALERTS_FILE` redirected to a tmp path via `monkeypatch`.
