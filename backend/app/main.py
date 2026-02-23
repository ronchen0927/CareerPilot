import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import jobs

# Logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="104 Job Scraper API",
    description="104 人力銀行職缺爬蟲 API",
    version="2.0.0",
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


@app.get("/")
async def root():
    return {
        "message": "104 Job Scraper API",
        "docs": "/docs",
        "version": "2.0.0",
    }
