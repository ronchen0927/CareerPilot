# CareerPilot Backend

This is the FastAPI backend service for CareerPilot. It handles the job scraping, AI processing, and scheduled alert background tasks.

## Quick Start

Please refer to the [main README.md](../README.md) in the project root for full environment setup and execution instructions.

```bash
uv sync --group dev
uv run playwright install chromium
uv run uvicorn app.main:app --reload --port 8000
```

## Architecture

- **FastAPI**: Core REST API framework, utilizing `pydantic` for request validation.
- **Scraping**: 
  - `aiohttp` for non-blocking HTTP requests to 104 and Yourator JSON APIs.
  - `Playwright` for extracting Next.js SSR data from CakeResume.
- **AI Processing**: Integration with OpenAI API for cover letter generation, resume rewriting, and job evaluation.
- **Database**: SQLite (via `aiosqlite`) for fast, async local storage of AI output history.

See [CLAUDE.md](../CLAUDE.md) for more detailed architectural notes and testing instructions.
