import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import init_db
from .routers import (
    alerts,
    chat,
    cover_letter,
    cv,
    evaluate,
    fetch_url,
    history,
    jobs,
    liveness,
    rag,
    resume,
)

# Logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .liveness import run_liveness_loop
    from .scheduler import run_scheduler

    await init_db()
    alert_task = asyncio.create_task(run_scheduler())
    liveness_task = asyncio.create_task(run_liveness_loop())
    yield
    for task in (alert_task, liveness_task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="CareerPilot API",
    description="AI 求職助理平台 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — 允許前端跨域請求
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (images etc.)
static_dir = Path(__file__).resolve().parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Routers
app.include_router(jobs.router)
app.include_router(alerts.router)
app.include_router(evaluate.router)
app.include_router(cv.router)
app.include_router(fetch_url.router)
app.include_router(history.router)
app.include_router(cover_letter.router)
app.include_router(resume.router)
app.include_router(liveness.router)
app.include_router(chat.router)
app.include_router(rag.router)


@app.get("/")
async def root():
    return {
        "message": "CareerPilot API",
        "docs": "/docs",
        "version": "1.0.0",
    }
