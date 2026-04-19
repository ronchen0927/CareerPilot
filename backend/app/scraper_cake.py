"""
CakeResume (cake.me) 非同步爬蟲。

CakeResume 的職缺搜尋為 client-side 渲染（Algolia），SSR 頁面的 __NEXT_DATA__
僅包含當前頁面的職缺資料。每次請求回傳約 10 筆職缺，
依照 `pageMap` 中 page 對應的路徑清單順序排列。

注意：SSR 頁面不支援 area / experience 篩選（篩選由前端 JS 執行），
因此這些參數目前不會影響爬取結果。

TODO: 待使用者提供 CakeResume 特定頁面區塊的結構後，
      可進一步確認正確的資料路徑與欄位對應，再調整以下實作。
"""

import asyncio
import json
import logging

import aiohttp
from bs4 import BeautifulSoup

from .models import JobListing, JobSearchRequest

logger = logging.getLogger(__name__)

CAKE_BASE_URL = "https://www.cake.me/jobs"

# CakeResume seniority level display mapping
SENIORITY_DISPLAY: dict[str, str] = {
    "entry_level": "1年以下",
    "junior": "1-3年",
    "mid_level": "3-5年",
    "mid_senior_level": "5年以上",
    "senior": "5-10年",
    "director": "10年以上",
    "no_preference": "不拘",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


def _build_url(keyword: str, page: int) -> str:
    """Build CakeResume search URL."""
    return f"{CAKE_BASE_URL}?keywords={keyword}&page={page}&locale=zh-TW"


def _extract_next_data(html: str) -> dict:
    """Extract __NEXT_DATA__ JSON from page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return {}
    try:
        return json.loads(tag.string)
    except json.JSONDecodeError as e:
        logger.error("解析 __NEXT_DATA__ 失敗: %s", e)
        return {}


def _extract_jobs_from_next_data(data: dict) -> list[dict]:
    """
    從 Next.js JSON 結構中取出職缺列表。

    資料路徑：
      props.pageProps.initialState.jobSearch.viewsByFilterKey
        → 第一個 key → pageMap → {'1': [path1, path2, ...]}
      props.pageProps.initialState.jobSearch.entityByPathId
        → {path: entity_dict}

    回傳 entity dict 的清單（已依 pageMap 排序）。
    """
    try:
        page_props = data.get("props", {}).get("pageProps", {})
        init_state = page_props.get("initialState", {})
        job_search = init_state.get("jobSearch", {})

        entity_by_path: dict[str, dict] = job_search.get("entityByPathId", {})
        views_by_filter: dict = job_search.get("viewsByFilterKey", {})

        if not views_by_filter:
            return []

        # Take the first filter key (usually '{"filters":{}}')
        first_view = next(iter(views_by_filter.values()))
        page_map: dict = first_view.get("pageMap", {})

        # Collect all paths from all pages in pageMap (SSR typically only has page 1)
        ordered_paths: list[str] = []
        for _page_num in sorted(page_map.keys(), key=lambda x: int(x)):
            ordered_paths.extend(page_map[_page_num])

        return [entity_by_path[p] for p in ordered_paths if p in entity_by_path]
    except Exception as e:
        logger.error("從 __NEXT_DATA__ 擷取職缺失敗: %s", e)
        return []


def _parse_salary(salary_obj: dict | None) -> tuple[int, int, str]:
    """Parse CakeResume salary object → (low, high, display_str)."""
    if not salary_obj:
        return 0, 0, "待遇面議"

    raw_min = salary_obj.get("min")
    raw_max = salary_obj.get("max")
    salary_type = salary_obj.get("type", "per_month")

    low = int(raw_min) if raw_min else 0
    high = int(raw_max) if raw_max else 0

    # Convert annual to monthly
    if salary_type == "per_year":
        low = low // 12
        high = high // 12

    if low == 0 and high == 0:
        return 0, 0, "待遇面議"
    if high == 0:
        return low, 0, f"{low:,}+ 元以上"
    return low, high, f"{low:,} ~ {high:,} 元"


def _parse_date(raw_date: str | None) -> str:
    """Normalize ISO datetime string → 'YYYY/MM/DD'."""
    if not raw_date:
        return "9999/12/31"
    # "2026-04-10T12:00:00.000Z" → "2026/04/10"
    return raw_date[:10].replace("-", "/")


def _parse_city(entity: dict) -> str:
    """Extract city display string from CakeResume entity."""
    locs_with_locale = entity.get("locationsWithLocale") or []
    for loc in locs_with_locale:
        if isinstance(loc, dict) and loc.get("zh-TW"):
            return loc["zh-TW"]
    locations = entity.get("locations") or []
    return locations[0] if locations else ""


def _parse_job(entity: dict) -> JobListing | None:
    """Parse a single CakeResume entity dict into JobListing."""
    try:
        path = entity.get("path", "")
        link = f"https://www.cake.me/jobs/{path}" if path else ""
        job_name = entity.get("title", "")
        page_obj = entity.get("page") or {}
        company = page_obj.get("name", "")
        city = _parse_city(entity)
        raw_date = entity.get("contentUpdatedAt") or entity.get("updatedAt", "")
        date = _parse_date(raw_date)
        seniority = entity.get("seniorityLevel", "")
        experience = SENIORITY_DISPLAY.get(seniority, seniority or "不拘")
        salary_low, salary_high, salary = _parse_salary(entity.get("salary"))

        return JobListing(
            job=job_name,
            date=date,
            link=link,
            company=company,
            city=city,
            experience=experience,
            education="不拘",  # CakeResume entity doesn't expose education requirement
            salary=salary,
            salary_low=salary_low,
            salary_high=salary_high,
            is_featured=False,
            source="CakeResume",
        )
    except Exception as e:
        logger.warning("解析 CakeResume 職缺時發生錯誤，跳過: %s", e)
        return None


async def _fetch_page(session: aiohttp.ClientSession, url: str) -> list[dict]:
    """Fetch one CakeResume search page and return raw entity dicts."""
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.error("CakeResume 回應 %d: %s", resp.status, url)
                return []
            html = await resp.text()
            next_data = _extract_next_data(html)
            return _extract_jobs_from_next_data(next_data)
    except Exception as e:
        logger.error("CakeResume 爬取失敗 %s: %s", url, e)
        return []


async def scrape_jobs(request: JobSearchRequest) -> list[JobListing]:
    """
    非同步爬取 CakeResume 職缺。

    因 SSR 限制，每個 URL 僅回傳約 10 筆職缺。
    多頁請求會同時發出，但 CakeResume 通常只在 SSR 中渲染第 1 頁，
    因此實際去重後可能與單頁結果相近。
    """
    urls = [_build_url(request.keyword, page) for page in range(1, request.pages + 1)]

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        results = await asyncio.gather(*[_fetch_page(session, url) for url in urls])

    seen_links: set[str] = set()
    all_jobs: list[JobListing] = []

    for page_items in results:
        for entity in page_items:
            job = _parse_job(entity)
            if job is None or not job.link:
                continue
            if job.link in seen_links:
                continue
            seen_links.add(job.link)
            all_jobs.append(job)

    all_jobs.sort(key=lambda j: j.date, reverse=True)
    return all_jobs
