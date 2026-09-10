"""Fetch LinkedIn's public guest job cards without login credentials.

Guest markup is not a stable API. Stop on access restrictions instead of retrying.
"""

import asyncio
import logging
import re
from datetime import date
from urllib.parse import urlencode, urlsplit

import aiohttp
from bs4 import BeautifulSoup

from .models import JobListing, JobSearchRequest

logger = logging.getLogger(__name__)
BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
PAGE_SIZE = 25
MAX_PAGES = 5
REQUEST_DELAY = 1.0


def _build_url(keyword: str, page: int) -> str:
    return f"{BASE_URL}?{urlencode({'keywords': keyword, 'location': 'Taiwan', 'start': (page - 1) * PAGE_SIZE, 'sortBy': 'DD'})}"


def _parse_jobs(html: str) -> list[JobListing]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for card in soup.select(".base-search-card, .job-search-card"):
        title = card.select_one(".base-search-card__title")
        anchor = card.select_one("a.base-card__full-link[href]")
        if title is None or anchor is None or not title.get_text(strip=True):
            continue
        url = urlsplit(str(anchor["href"]))
        if url.scheme != "https" or not (
            url.hostname == "linkedin.com" or (url.hostname or "").endswith(".linkedin.com")
        ):
            continue
        match = re.fullmatch(r"/jobs/view/(?:[^/]*-)?(\d+)/?", url.path)
        if not match:
            continue
        company = card.select_one(".base-search-card__subtitle")
        location = card.select_one(".job-search-card__location")
        posted = card.select_one("time[datetime]")
        posted_date = ""
        if posted:
            try:
                posted_date = date.fromisoformat(str(posted["datetime"])[:10]).strftime("%Y/%m/%d")
            except ValueError:
                pass
        jobs.append(
            JobListing(
                job=title.get_text(" ", strip=True),
                company=company.get_text(" ", strip=True) if company else "",
                city=location.get_text(" ", strip=True) if location else "",
                date=posted_date,
                link=f"https://www.linkedin.com/jobs/view/{match[1]}",
                experience="未提供",
                education="未提供",
                salary="未提供",
                source="LinkedIn",
            )
        )
    return jobs


async def scrape_jobs(request: JobSearchRequest) -> list[JobListing]:
    jobs: dict[str, JobListing] = {}
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        },
    ) as session:
        for page in range(1, min(request.pages, MAX_PAGES) + 1):
            if page > 1:
                await asyncio.sleep(REQUEST_DELAY)
            try:
                async with session.get(
                    _build_url(request.keyword, page), allow_redirects=False
                ) as response:
                    if response.status != 200:
                        logger.warning("LinkedIn 回應 HTTP %s，停止抓取", response.status)
                        break
                    html = await response.text()
            except (TimeoutError, aiohttp.ClientError) as exc:
                logger.warning("LinkedIn 爬取失敗，保留已取得結果: %s", exc)
                break
            page_jobs = _parse_jobs(html)
            new_jobs = {job.link: job for job in page_jobs if job.link not in jobs}
            if not new_jobs:
                break
            jobs.update(new_jobs)
    return sorted(jobs.values(), key=lambda job: job.date, reverse=True)
