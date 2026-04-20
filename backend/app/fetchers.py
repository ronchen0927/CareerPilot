"""Shared HTTP fetch helpers used by the URL-fetch endpoint and the liveness checker."""

import logging
import re

import aiohttp
import trafilatura
from goose3 import Goose
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

FETCH_TIMEOUT_S = 15
FETCH_TIMEOUT_MS = 15_000

_NOSCRIPT_RE = re.compile(r"<noscript\b[^>]*>.*?</noscript>", re.DOTALL | re.IGNORECASE)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


def parse_html(html: str) -> str:
    """Extract main content from HTML using trafilatura → Goose3 fallback."""
    html = _NOSCRIPT_RE.sub("", html)
    text = trafilatura.extract(html, include_comments=False, include_tables=True)
    if text and text.strip():
        return text.strip()
    try:
        g = Goose()
        article = g.extract(raw_html=html)
        text = article.cleaned_text
        if text and text.strip():
            return text.strip()
    except Exception:
        pass
    return ""


async def fetch_with_aiohttp(url: str) -> str | None:
    """Try to fetch the page with aiohttp + trafilatura/Goose3. Returns None on failure."""
    try:
        timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT_S)
        async with aiohttp.ClientSession(headers=_HEADERS, timeout=timeout) as session:
            async with session.get(url, ssl=False) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
        return parse_html(html) or None
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
