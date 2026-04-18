import time

from fastapi import APIRouter

from ..config import AREA_OPTIONS, EXPERIENCE_OPTIONS
from ..models import JobSearchRequest, JobSearchResponse
from ..scraper import scrape_jobs as scrape_104

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
    """搜尋職缺（104 人力銀行）"""
    start = time.perf_counter()
    jobs = await scrape_104(request)
    jobs.sort(key=lambda j: j.date, reverse=True)
    elapsed = time.perf_counter() - start
    return JobSearchResponse(
        results=jobs,
        count=len(jobs),
        elapsed_time=round(elapsed, 2),
    )
