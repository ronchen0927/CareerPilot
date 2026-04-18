"""Shared HTTP fetch helpers used by the URL-fetch endpoint and the liveness checker."""

import logging
import re

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

FETCH_TIMEOUT_S = 15
FETCH_TIMEOUT_MS = 15_000

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

_NOISE_TAGS = {
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "iframe",
    "noscript",
    "button",
    "svg",
}


def parse_html(html: str) -> str:
    """Strip noise from HTML and return the main content as plain text."""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"id": re.compile(r"job|content|detail", re.I)})
        or soup.find(attrs={"class": re.compile(r"job|content|detail|description", re.I)})
        or soup.body
    )

    raw = main.get_text(separator="\n") if main else soup.get_text(separator="\n")

    lines = [ln.strip() for ln in raw.splitlines()]
    cleaned: list[str] = []
    prev_blank = False
    for ln in lines:
        if not ln:
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
        else:
            cleaned.append(ln)
            prev_blank = False

    return "\n".join(cleaned).strip()


async def fetch_with_aiohttp(url: str) -> str | None:
    """Try to fetch the page with aiohttp + BeautifulSoup. Returns None on failure."""
    try:
        timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT_S)
        async with aiohttp.ClientSession(headers=_HEADERS, timeout=timeout) as session:
            async with session.get(url, ssl=False) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
        return parse_html(html)
    except Exception as e:
        logger.debug("aiohttp fetch failed for %s: %s", url, e)
        return None


async def fetch_with_playwright(url: str) -> str:
    """Fallback: launch headless Chromium and extract text content."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_extra_http_headers({"User-Agent": _HEADERS["User-Agent"]})
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=FETCH_TIMEOUT_MS)
            await page.wait_for_load_state("networkidle", timeout=FETCH_TIMEOUT_MS)
        except PlaywrightTimeout:
            pass
        html = await page.content()
        await browser.close()
    return parse_html(html)
