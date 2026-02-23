import time

from fastapi import APIRouter

from ..config import AREA_OPTIONS, EXPERIENCE_OPTIONS
from ..models import JobSearchRequest, JobSearchResponse
from ..scraper import scrape_jobs

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/options")
async def get_options():
    """回傳地區 & 經歷選項清單，供前端渲染表單使用"""
    return {
        "areas": AREA_OPTIONS,
        "experience": EXPERIENCE_OPTIONS,
    }


@router.post("/search", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest):
    """搜尋 104 職缺"""
    start = time.perf_counter()
    results = await scrape_jobs(request)
    elapsed = time.perf_counter() - start

    return JobSearchResponse(
        results=results,
        count=len(results),
        elapsed_time=round(elapsed, 2),
    )
