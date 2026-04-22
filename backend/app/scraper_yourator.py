"""
Yourator (yourator.co) 非同步爬蟲。

使用 Yourator 內部 JSON API (/api/v4/jobs)，每頁回傳最多 20 筆職缺。
Salary 為字串格式，如 "NT$ 500,000 - 700,000 (年薪)"，需自行解析。
lastActiveAt 為相對時間字串，無法轉換為絕對日期，以今日為準。
"""

import asyncio
import logging
import re
from datetime import datetime
from urllib.parse import urlencode

import aiohttp

from .models import JobListing, JobSearchRequest

logger = logging.getLogger(__name__)

YOURATOR_API = "https://www.yourator.co/api/v4/jobs"
YOURATOR_BASE = "https://www.yourator.co"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.yourator.co/jobs",
}

_AREA_TO_YOURATOR_CODE: dict[str, str] = {
    "6001001000": "TPE",
    "6001002000": "NWT",
    "6001006000": "HSQ",
    "6001008000": "TXG",
    "6001014000": "TNN",
    "6001016000": "KHH",
}

_EXP_TO_YOURATOR: dict[str, str] = {
    "1": "less_than_1",
    "3": "1_3_years",
    "5": "3_5_years",
    "10": "5_10_years",
    "99": "over_10_years",
}


def _build_url(
    keyword: str,
    page: int,
    areas: list[str] | None = None,
    experience: list[str] | None = None,
    categories: list[str] | None = None,
    salary_min: int = 0,
    salary_max: int = 0,
) -> str:
    params: list[tuple[str, str]] = [
        ("term[]", keyword),
        ("page", str(page)),
        ("sort", "most_related"),
    ]
    for code in areas or []:
        area_code = _AREA_TO_YOURATOR_CODE.get(code)
        if area_code:
            params.append(("area[]", area_code))
    for code in experience or []:
        exp = _EXP_TO_YOURATOR.get(code)
        if exp:
            params.append(("years_of_exp[]", exp))
    for cat in categories or []:
        params.append(("category[]", cat))
    if salary_min > 0 or salary_max > 0:
        low = salary_min if salary_min > 0 else 0
        high = salary_max if salary_max > 0 else 0
        params.append(("monthly", f"{low},{high}"))
    return f"{YOURATOR_API}?{urlencode(params)}"


def _parse_salary(salary_str: str | None) -> tuple[int, int, str]:
    """Parse Yourator salary string → (low, high, display_str).

    Examples:
      "NT$ 500,000 - 700,000 (年薪)"
      "NT$ 50,000 (月薪)"
      "面議"
    """
    if not salary_str or salary_str.strip() in ("面議", "待遇面議"):
        return 0, 0, "待遇面議"

    nums = [int(n.replace(",", "")) for n in re.findall(r"[\d,]+", salary_str)]
    if not nums:
        return 0, 0, salary_str

    is_annual = "年薪" in salary_str

    low = nums[0]
    high = nums[1] if len(nums) >= 2 else 0

    if is_annual:
        low = low // 12
        high = high // 12 if high else 0

    if low == 0 and high == 0:
        return 0, 0, "待遇面議"
    if high == 0:
        return low, 0, f"{low:,}+ 元以上"
    return low, high, f"{low:,} ~ {high:,} 元"


def _parse_job(item: dict) -> JobListing | None:
    try:
        path = item.get("path", "")
        link = f"{YOURATOR_BASE}{path}" if path else ""
        job_name = item.get("name", "")
        company_obj = item.get("company") or {}
        company = company_obj.get("brand", "")
        city = item.get("location", "")
        salary_low, salary_high, salary = _parse_salary(item.get("salary"))
        date = datetime.now().strftime("%Y/%m/%d")

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
            source="Yourator",
        )
    except Exception as e:
        logger.warning("解析 Yourator 職缺時發生錯誤，跳過: %s", e)
        return None


async def _fetch_page(session: aiohttp.ClientSession, url: str) -> list[dict]:
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.error("Yourator 回應 %d: %s", resp.status, url)
                return []
            data = await resp.json()
            payload = data.get("payload", {})
            return payload.get("jobs", [])
    except Exception as e:
        logger.error("Yourator 爬取失敗 %s: %s", url, e)
        return []


async def scrape_jobs(request: JobSearchRequest) -> list[JobListing]:
    """非同步爬取 Yourator 職缺，每頁約 20 筆。"""
    urls = [
        _build_url(
            request.keyword,
            page,
            request.areas,
            request.experience,
            request.categories,
            request.salary_min,
            request.salary_max,
        )
        for page in range(1, request.pages + 1)
    ]
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        results = await asyncio.gather(*[_fetch_page(session, url) for url in urls])

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

    return all_jobs
