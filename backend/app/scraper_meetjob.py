"""
MeetJob (meet.jobs) 非同步爬蟲。

使用 MeetJob 後端 JSON API (https://api.meet.jobs/api/v1/jobs)。
以 location=tw 篩選台灣職缺，每頁最多 20 筆。
Salary 為結構化物件，支援月薪與年薪，年薪自動換算為月薪。
"""

import asyncio
import logging

import aiohttp

from .models import JobListing, JobSearchRequest

logger = logging.getLogger(__name__)

MEETJOB_API = "https://api.meet.jobs/api/v1/jobs"
MEETJOB_BASE = "https://meet.jobs"

# Normalize English city names returned by the API to Traditional Chinese
_CITY_MAP: dict[str, str] = {
    "Taipei City": "台北市",
    "Taipei": "台北市",
    "New Taipei City": "新北市",
    "Taoyuan City": "桃園市",
    "Hsinchu City": "新竹市",
    "Hsinchu": "新竹市",
    "Taichung City": "台中市",
    "Taichung": "台中市",
    "Tainan City": "台南市",
    "Kaohsiung City": "高雄市",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Origin": "https://meet.jobs",
    "Referer": "https://meet.jobs/jobs",
}


def _build_url(keyword: str, page: int) -> str:
    return f"{MEETJOB_API}?query={keyword}&location=tw&page={page}"


def _parse_salary(salary_obj: dict | None) -> tuple[int, int, str]:
    """Parse MeetJob salary object → (low, high, display_str)."""
    if not salary_obj:
        return 0, 0, "待遇面議"

    raw_min = salary_obj.get("minimum")
    raw_max = salary_obj.get("maximum")
    paid_period = salary_obj.get("paid_period_key", "monthly")

    low = int(raw_min) if raw_min else 0
    high = int(raw_max) if raw_max else 0

    if paid_period == "annually":
        low = low // 12
        high = high // 12 if high else 0

    if low == 0 and high == 0:
        return 0, 0, "待遇面議"
    if high == 0:
        return low, 0, f"{low:,}+ 元以上"
    return low, high, f"{low:,} ~ {high:,} 元"


def _parse_date(raw_date: str | None) -> str:
    """ISO datetime → 'YYYY/MM/DD'."""
    if not raw_date:
        return "9999/12/31"
    return raw_date[:10].replace("-", "/")


def _parse_city(address: dict | None) -> str:
    if not address:
        return ""
    place = address.get("place") or {}
    city = place.get("city") or address.get("handwriting_city") or ""
    return _CITY_MAP.get(city, city)


def _parse_job(item: dict) -> JobListing | None:
    try:
        job_id = item.get("id", "")
        slug = item.get("slug", "")
        link = f"{MEETJOB_BASE}/zh-TW/jobs/{job_id}-{slug}" if job_id else ""
        job_name = (item.get("title") or "").strip()
        employer = item.get("employer") or {}
        company = employer.get("name", "")
        city = _parse_city(item.get("address"))
        date = _parse_date(item.get("published_at") or item.get("updated_at"))
        salary_low, salary_high, salary = _parse_salary(item.get("salary"))

        return JobListing(
            job=job_name,
            date=date,
            link=link,
            company=company,
            city=city,
            experience="不拘",
            education="不拘",
            salary=salary,
            salary_low=salary_low,
            salary_high=salary_high,
            is_featured=False,
            source="MeetJob",
        )
    except Exception as e:
        logger.warning("解析 MeetJob 職缺時發生錯誤，跳過: %s", e)
        return None


async def _fetch_page(session: aiohttp.ClientSession, keyword: str, page: int) -> list[dict]:
    url = _build_url(keyword, page)
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.error("MeetJob 回應 %d: %s", resp.status, url)
                return []
            data = await resp.json()
            return data.get("collection", [])
    except Exception as e:
        logger.error("MeetJob 爬取失敗 %s: %s", url, e)
        return []


async def scrape_jobs(request: JobSearchRequest) -> list[JobListing]:
    """非同步爬取 MeetJob 台灣職缺，每頁最多 20 筆。"""
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        results = await asyncio.gather(
            *[_fetch_page(session, request.keyword, page) for page in range(1, request.pages + 1)]
        )

    seen_links: set[str] = set()
    all_jobs: list[JobListing] = []

    for page_items in results:
        for item in page_items:
            job = _parse_job(item)
            if job is None or not job.link:
                continue
            if job.link in seen_links:
                continue
            seen_links.add(job.link)
            all_jobs.append(job)

    all_jobs.sort(key=lambda j: j.date, reverse=True)
    return all_jobs
