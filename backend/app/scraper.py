import asyncio
import datetime
import logging
import ssl

import aiohttp

from .config import settings
from .models import JobListing, JobSearchRequest

logger = logging.getLogger(__name__)


# Education mapping
EDU_MAP = {
    1: "國中",
    2: "高中",
    3: "專科",
    4: "大學",
    5: "碩士",
    6: "博士",
}

# Experience / period mapping
PERIOD_MAP = {
    0: "不拘",
    1: "1年以下",
    2: "1-3年",
    3: "3-5年",
    4: "5-10年",
    5: "10年以上",
}


def _format_salary(low: int, high: int) -> str:
    """Format salary range into readable string."""
    if low == 0 and high == 0:
        return "待遇面議"
    if high >= 9999999:
        return f"{low:,}+ 元以上"
    return f"{low:,} ~ {high:,} 元"


def _format_date(date_str: str) -> str:
    """Format date string from '20260223' to '2026/02/23'."""
    if not date_str or len(date_str) != 8:
        return date_str
    return f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:]}"


def _format_edu(edu_list: list[int]) -> str:
    """Format education requirement."""
    if not edu_list:
        return "不拘"
    # Return the lowest (minimum) education required
    min_edu = min(edu_list)
    return EDU_MAP.get(min_edu, "不拘")


def _build_url(keyword: str, area: str, page: int, jobexp: str) -> str:
    """Build 104 API URL."""
    params = (
        f"keyword={keyword}"
        f"&order=15"
        f"&page={page}"
        f"&mode=s"
        f"&jobsource=2021indexpoc"
        f"&ro=0"
    )
    if area:
        params += f"&area={area}"
    if jobexp:
        params += f"&jobexp={jobexp}"
    return f"{settings.BASE_URL}?{params}"


def _sort_key(job: JobListing) -> str:
    """Sort key by date descending."""
    return job.date


def _create_ssl_context() -> ssl.SSLContext:
    """Create an SSL context that skips cert verification (for 104.com.tw)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _parse_job(item: dict) -> JobListing | None:
    """Parse a single job item from the API response."""
    try:
        job_name = item.get("jobName", "")
        appear_date = _format_date(item.get("appearDate", ""))
        link_obj = item.get("link", {})
        job_link = link_obj.get("job", "") if isinstance(link_obj, dict) else ""
        company = item.get("custName", "")
        city = item.get("jobAddrNoDesc", "")
        period = item.get("period", 0)
        experience = PERIOD_MAP.get(period, "不拘")
        education = _format_edu(item.get("optionEdu", []))
        salary_low_val = item.get("salaryLow", 0)
        salary_high_val = item.get("salaryHigh", 0)
        salary = _format_salary(salary_low_val, salary_high_val)

        # Featured jobs don't have a normal date
        is_featured = item.get("jobRo", 0) == 1 and not appear_date

        return JobListing(
            job=job_name,
            date=appear_date or "9999/12/31",
            link=job_link,
            company=company,
            city=city,
            experience=experience,
            education=education,
            salary=salary,
            salary_low=salary_low_val,
            salary_high=salary_high_val,
            is_featured=is_featured,
        )
    except Exception as e:
        logger.warning("解析職缺時發生錯誤，跳過: %s", e)
        return None


async def scrape_jobs(request: JobSearchRequest) -> list[JobListing]:
    """
    使用 104 內部 JSON API 非同步爬取職缺。

    同時請求所有頁面以提高效率。
    """
    area_str = "%2C".join(request.areas) if request.areas else ""
    exp_str = "%2C".join(request.experience) if request.experience else ""

    urls = [
        _build_url(request.keyword, area_str, page, exp_str)
        for page in range(1, request.pages + 1)
    ]

    headers = {
        "Referer": "https://www.104.com.tw/jobs/search/",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
    }

    ssl_ctx = _create_ssl_context()
    connector = aiohttp.TCPConnector(ssl=ssl_ctx)

    async def fetch(session: aiohttp.ClientSession, url: str) -> list[dict]:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error("API 回應 %d: %s", response.status, url)
                    return []
                data = await response.json()
                return data.get("data", [])
        except Exception as e:
            logger.error("爬取失敗 %s: %s", url, e)
            return []

    async with aiohttp.ClientSession(
        connector=connector, headers=headers
    ) as session:
        tasks = [fetch(session, url) for url in urls]
        results = await asyncio.gather(*tasks)

    seen_links: set[str] = set()
    all_jobs: list[JobListing] = []

    for page_items in results:
        for item in page_items:
            job = _parse_job(item)
            if job is None:
                continue
            if job.link in seen_links:
                continue
            seen_links.add(job.link)
            all_jobs.append(job)

    all_jobs.sort(key=_sort_key, reverse=True)
    return all_jobs
