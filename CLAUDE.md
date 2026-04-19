# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
cd backend
uv sync --group dev                               # Install dependencies (incl. dev tools)
uv run playwright install chromium                # Install Chromium for Playwright (first time)
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
npm install        # Install dependencies (first time)
npm run dev        # Start dev server at http://localhost:5173
npm run build      # Build for production
npx tsc --noEmit   # Type-check without emitting files
```

`API_BASE` is hardcoded to `http://localhost:8000` in `frontend/src/api/client.ts`.

## Architecture

```
backend/
  app/
    main.py           # FastAPI app: CORS, static files, lifespan (starts scheduler task)
    config.py         # Settings (pydantic-settings), AREA_OPTIONS, EXPERIENCE_OPTIONS constants
    models.py         # Pydantic models: JobSearchRequest, JobListing, AlertCreateRequest, etc.
    scraper.py        # Async scraper hitting 104's internal JSON API via aiohttp
    scraper_cake.py   # Async scraper for CakeResume via aiohttp + BeautifulSoup
    alerts.py         # load_alerts() / save_alerts() — persists to backend/alerts.json
    scheduler.py      # Background asyncio loop: checks due alerts, scrapes, notifies
    routers/
      jobs.py         # POST /api/jobs/search, GET /api/jobs/options
      alerts.py       # GET/POST /api/alerts, DELETE /api/alerts/{id}, POST /{id}/trigger
      evaluate.py     # POST /api/jobs/evaluate (structured), POST /api/jobs/evaluate-text (free text)
      cv.py           # POST /api/cv/parse — extract text from uploaded PDF via pdfplumber
      fetch_url.py    # POST /api/jobs/fetch-url — fetch job page via Playwright (headless Chromium)
      chat.py         # POST /api/chat — streaming per-job Q&A via StreamingResponse
      cover_letter.py # POST /api/jobs/cover-letter, GET /api/cover-letters, GET /api/cover-letters/{id}
      resume.py       # POST /api/jobs/resume-rewrite, GET /api/resume-rewrites, GET /api/resume-rewrites/{id}
      history.py      # GET /api/history, GET /api/history/{id} — evaluation history records
      liveness.py     # GET /api/liveness — health check
  tests/
    conftest.py         # Fixtures: tmp_alerts_file (monkeypatches ALERTS_FILE), client (TestClient)
    test_scraper.py
    test_scraper_cake.py
    test_scheduler.py
    test_alerts_storage.py
    test_api_jobs.py
    test_api_alerts.py
    test_api_chat.py
frontend/
  src/
    main.tsx            # React entry point
    App.tsx             # Routes: / | /dashboard | /alerts | /evaluate | /history | /cover-letter | /cover-letters | /resume-rewrite | /resume-rewrites | /settings
    api/
      client.ts         # All fetch calls to the backend API
    components/
      Layout.tsx        # Left sidebar nav (220px), mobile hamburger overlay, theme toggle
      JobModal.tsx      # Job detail modal with AI evaluation + per-job chat (JobChat)
      JobChat.tsx       # Per-job multi-turn Q&A chat with streaming responses
      CVModal.tsx       # CV input modal (used on search page)
      DimensionsPanel.tsx # Collapsible AI score breakdown panel
      CheckboxGroup.tsx # Reusable checkbox filter group
    pages/
      SearchPage.tsx    # Main search page + bookmarks list
      DashboardPage.tsx # Kanban board (drag-and-drop job status tracking)
      AlertsPage.tsx    # Scheduled alert management UI
      EvaluatePage.tsx  # AI job evaluation: URL fetch or paste JD + PDF CV upload
      HistoryPage.tsx / HistoryDetailPage.tsx
      CoverLetterPage.tsx / CoverLetterHistoryPage.tsx / CoverLetterDetailPage.tsx
      ResumeRewritePage.tsx / ResumeRewriteHistoryPage.tsx / ResumeRewriteDetailPage.tsx
      SettingsPage.tsx  # User preferences (job prefs stored via usePreferences)
    hooks/
      useBookmarks.ts   # Bookmark CRUD backed by localStorage
      useLocalStorage.ts
      useTheme.ts
      usePreferences.ts # User job preferences (stored in localStorage)
      useLiveness.ts    # Polls GET /api/liveness to check backend connectivity
    types/
      index.ts          # Shared TypeScript interfaces
static/                 # Served at /static by FastAPI
```

**Data flow:** Frontend form → `POST /api/jobs/search` → `scraper.scrape_jobs()` / `scraper_cake.scrape_cake_jobs()` fetch concurrently via `asyncio.gather` → deduplicates by job link → sorts by date descending → returns `JobSearchResponse`.

**104 API:** Targets `https://www.104.com.tw/jobs/search/api/jobs` with a `Referer` header and SSL cert verification disabled (104 cert quirk). Area and experience codes are URL-encoded comma-joined lists.

**CakeResume scraper:** Hits `https://www.cakeresume.com/jobs` HTML pages via aiohttp + BeautifulSoup. Parses job cards from the rendered HTML.

**AI Evaluation:** Two modes — structured (`/evaluate`, takes a `JobListing` object) and free-text (`/evaluate-text`, takes raw JD string). Both share `_make_openai_client` / `_call_openai` helpers. The free-text endpoint is used by `EvaluatePage`. Requires `OPENAI_API_KEY` in `.env`.

**Per-job Q&A Chat:** `POST /api/chat` streams an OpenAI response via `StreamingResponse` (`text/plain; charset=utf-8`). System prompt is English; output is Traditional Chinese. Injects job details + user CV + preferences into context. Frontend reads the stream with `fetch` + `ReadableStream`.

**PDF CV parse:** `POST /api/cv/parse` accepts multipart PDF upload (max 5 MB), extracts text via `pdfplumber`, returns `{ text }`. Frontend populates the CV textarea and persists to `localStorage`.

**Playwright URL fetch:** `POST /api/jobs/fetch-url` launches headless Chromium, navigates to the URL with a browser-like User-Agent, waits for `networkidle`, returns `innerText` (capped at 8000 chars). Returns 422 if content is too short (likely blocked), prompting the user to paste manually.

**Scheduler:** Runs as an asyncio task inside the FastAPI `lifespan` context manager (no external dependency). Wakes every 60 seconds, checks each alert's `interval_minutes` against `last_run`, scrapes if due, sends Line Notify or Webhook, updates `seen_links` and `last_run` in `alerts.json`.

**Frontend state:** Bookmarks and kanban status stored in `localStorage`. CV text stored under key `careerpilot_cv`. Per-job chat history stored under key `careerpilot_chats` (object keyed by job URL). User preferences stored under key `careerpilot_prefs`.

## Testing approach

- Pure-function unit tests (scraper helpers, `_is_due`) need no mocking.
- API tests use `TestClient` with `scrape_jobs` mocked via `AsyncMock` and `ALERTS_FILE` redirected to a `tmp_path` via `monkeypatch` — no real network, no real files left behind.
- `run_scheduler` is replaced with `AsyncMock` in the `client` fixture so the lifespan completes instantly.
- When patching functions that are imported lazily inside a function body (e.g. `_fetch_new_jobs` in `trigger_alert`), patch the source module (`app.scheduler`) not the importing module (`app.routers.alerts`).
- AI endpoint tests must mock `settings.OPENAI_API_KEY` (e.g. `patch("app.routers.chat.settings")` with `mock_settings.OPENAI_API_KEY = "sk-test"`) — otherwise the 503 guard fires in CI where no `.env` exists.
