"""
Michael Page 台灣 (michaelpage.com.tw) 非同步爬蟲。

解析 Drupal SSR 搜尋頁 /zh/jobs/{keyword}，每頁 30 筆，分頁參數 ?page=0 起算。
無結果或超過最後一頁時回應 404。卡片不含薪資與日期；日期取自 ref 編號
（jn-MMYYYY-id）中的刊登年月。公司為獵頭客戶，不公開。

robots.txt 禁止 /search/ 與薪資/合約篩選參數，故只用關鍵字路徑 + page。
"""

import asyncio
import logging
import re
from urllib.parse import quote

import aiohttp
from bs4 import BeautifulSoup

from .models import JobListing, JobSearchRequest

logger = logging.getLogger(__name__)

MP_BASE = "https://www.michaelpage.com.tw"
PAGE_SIZE = 30
MAX_PAGES = 5
REQUEST_DELAY = 1.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

_REF_DATE_RE = re.compile(r"/ref/jn-(\d{2})(\d{4})-")


def _build_url(keyword: str, page: int) -> str:
    """page 為 1 起算；Drupal pager 為 0 起算。"""
    url = f"{MP_BASE}/zh/jobs/{quote(keyword, safe='')}"
    return f"{url}?page={page - 1}" if page > 1 else url


def _parse_date(link: str) -> str:
    # ponytail: ref only encodes year/month; fetch detail JSON-LD datePosted if day precision matters
    m = _REF_DATE_RE.search(link)
    return f"{m[2]}/{m[1]}/01" if m else ""


def _parse_jobs(html: str) -> list[JobListing]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for tile in soup.select(".search-job-tile"):
        anchor = tile.select_one(".job-title a[href]")
        if anchor is None or not anchor.get_text(strip=True):
            continue
        # 英文職缺的 href 帶 ?lang=zh-hant，保留以顯示中文版
        path = str(anchor["href"])
        if not path.startswith(("/job-detail/", "/zh/job-detail/")):
            continue
        link = f"{MP_BASE}{path}"
        location = tile.select_one(".job-location")
        jobs.append(
            JobListing(
                job=anchor.get_text(" ", strip=True),
                date=_parse_date(path),
                link=link,
                company="Michael Page（客戶不公開）",
                city=location.get_text(" ", strip=True) if location else "",
                experience="不拘",
                education="不拘",
                salary="待遇面議",
                source="MichaelPage",
            )
        )
    return jobs


async def scrape_jobs(request: JobSearchRequest) -> list[JobListing]:
    """依序爬取 Michael Page 搜尋頁，遇到 404 / 錯誤 / 不滿一頁即停止。"""
    seen_links: set[str] = set()
    all_jobs: list[JobListing] = []
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        for page in range(1, min(request.pages, MAX_PAGES) + 1):
            if page > 1:
                await asyncio.sleep(REQUEST_DELAY)
            url = _build_url(request.keyword, page)
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        if resp.status != 404:
                            logger.error("Michael Page 回應 %d: %s", resp.status, url)
                        break
                    html = await resp.text()
            except Exception as e:
                logger.error("Michael Page 爬取失敗 %s: %s", url, e)
                break

            page_jobs = _parse_jobs(html)
            for job in page_jobs:
                if job.link not in seen_links:
                    seen_links.add(job.link)
                    all_jobs.append(job)
            if len(page_jobs) < PAGE_SIZE:
                break

    return all_jobs
