import asyncio
import time

from fastapi import APIRouter

from ..config import AREA_OPTIONS, EXPERIENCE_OPTIONS
from ..models import JobSearchRequest, JobSearchResponse
from ..scraper import scrape_jobs as scrape_104
from ..scraper_cake import scrape_jobs as scrape_cake
from ..scraper_yourator import scrape_jobs as scrape_yourator

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
    """搜尋職缺（支援 104 / CakeResume / Yourator）"""
    # Dict built at call time so unit-test patches on individual scraper names take effect
    scrapers = {
        "104": scrape_104,
        "cake": scrape_cake,
        "yourator": scrape_yourator,
    }
    sources = [s for s in (request.sources or ["104"]) if s in scrapers]
    if not sources:
        sources = ["104"]

    start = time.perf_counter()
    results = await asyncio.gather(*[scrapers[s](request) for s in sources])

    seen: set[str] = set()
    all_jobs = []
    for job_list in results:
        for job in job_list:
            if job.link not in seen:
                seen.add(job.link)
                all_jobs.append(job)

    all_jobs.sort(key=lambda j: j.date, reverse=True)
    elapsed = time.perf_counter() - start
    return JobSearchResponse(
        results=all_jobs,
        count=len(all_jobs),
        elapsed_time=round(elapsed, 2),
    )
