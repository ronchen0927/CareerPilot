"""
CakeResume (cake.me) 非同步爬蟲。

CakeResume 的職缺搜尋為 client-side 渲染（Algolia），SSR 頁面的 __NEXT_DATA__
僅包含當前頁面的職缺資料。每次請求回傳約 10 筆職缺，
依照 `pageMap` 中 page 對應的路徑清單順序排列。

注意：CakeResume 支援 city[] 與 years_of_experience[] 參數進行篩選，
但 SSR 渲染的筆數有限，因此最多只抓取 MAX_PAGES 頁。
"""

import json
import logging
from urllib.parse import quote, urlencode

from playwright.async_api import Page, async_playwright

from .models import JobListing, JobSearchRequest

logger = logging.getLogger(__name__)

CAKE_BASE_URL = "https://www.cake.me/jobs"

# Maximum pages to fetch from CakeResume SSR (beyond this, results are typically empty/duplicates)
MAX_PAGES = 3

# Map 104 area codes → CakeResume location strings (中文格式 e.g. 台北市-台灣)
_AREA_TO_CAKE_CITY: dict[str, str] = {
    "6001001000": "台北市-台灣",
    "6001002000": "新北市-台灣",
    "6001006000": "新竹市-台灣",
    "6001008000": "台中市-台灣",
    "6001014000": "台南市-台灣",
    "6001016000": "高雄市-台灣",
}

# Map frontend experience codes → CakeResume seniority_levels values
# CakeResume 的年資篩選以「等級」為指（初階/中高階），參數名為 seniority_levels
_EXP_TO_CAKE: dict[str, str] = {
    "1": "entry_level",  # 1年以下 → 初階
    "3": "junior",  # 1-3年  → 初階
    "5": "mid_level",  # 3-5年  → 中階
    "10": "mid_senior_level",  # 5-10年 → 中高階
    "99": "director",  # 10年以上 → 高階
}

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


def _build_url(
    keyword: str,
    page: int,
    areas: list[str] | None = None,
    experience: list[str] | None = None,
) -> str:
    """Build CakeResume search URL.

    CakeResume 的正確格式為：
      https://www.cake.me/jobs/{keyword}?locations=台北市-台灣,新北市-台灣&page=2&...
    關鍵字放在路徑（path），地區用逗號分隔放在 locations 參數（中文格式）。
    """
    # Keyword goes in the URL path, not as a query param
    encoded_keyword = quote(keyword, safe="")
    base = f"{CAKE_BASE_URL}/{encoded_keyword}"

    params: list[tuple[str, str]] = [
        ("page", str(page)),
        ("locale", "zh-TW"),
    ]

    cake_locations = []
    for area_code in areas or []:
        city_slug = _AREA_TO_CAKE_CITY.get(area_code)
        if city_slug:
            cake_locations.append(city_slug)

    if cake_locations:
        params.append(("locations", ",".join(cake_locations)))

    cake_seniority = []
    for exp_code in experience or []:
        cake_exp = _EXP_TO_CAKE.get(exp_code)
        if cake_exp:
            cake_seniority.append(cake_exp)

    if cake_seniority:
        params.append(("seniority_levels", ",".join(cake_seniority)))

    return f"{base}?{urlencode(params, doseq=True)}"


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
        page_obj = entity.get("page") or {}
        company_path = page_obj.get("path", "")
        link = (
            f"https://www.cake.me/companies/{company_path}/jobs/{path}"
            if company_path and path
            else f"https://www.cake.me/jobs/{path}"
        )
        job_name = entity.get("title", "")
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


async def _fetch_page(page: Page, url: str) -> list[dict]:
    """Fetch one CakeResume search page and return raw entity dicts."""
    try:
        await page.goto(url, wait_until="domcontentloaded")
        next_data_str = await page.evaluate(
            "() => { const el = document.getElementById('__NEXT_DATA__'); return el ? el.textContent : null; }"
        )
        if not next_data_str:
            return []
        next_data = json.loads(next_data_str)
        return _extract_jobs_from_next_data(next_data)
    except Exception as e:
        logger.error("CakeResume 爬取失敗 %s: %s", url, e)
        return []


async def scrape_jobs(request: JobSearchRequest) -> list[JobListing]:
    """
    非同步爬取 CakeResume 職缺。

    因 SSR 限制，每個 URL 僅回傳約 10 筆職缺。
    最多抓取 MAX_PAGES 頁，並支援 area/experience 篩選。
    """
    pages_to_fetch = min(request.pages, MAX_PAGES)
    urls = [
        _build_url(request.keyword, page, request.areas, request.experience)
        for page in range(1, pages_to_fetch + 1)
    ]

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=HEADERS.get("User-Agent"))
        for url in urls:
            page = await context.new_page()
            page_results = await _fetch_page(page, url)
            results.append(page_results)
            await page.close()
        await browser.close()

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
