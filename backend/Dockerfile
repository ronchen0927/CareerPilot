# CareerPilot backend — FastAPI + uv + Playwright (Chromium)
FROM python:3.13-slim

# Install uv (official distroless image copy)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Install dependencies first (cached layer — only invalidated when lockfile changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Install Chromium + required system libraries for Playwright
RUN uv run playwright install --with-deps chromium

# Copy application code
COPY app ./app
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
