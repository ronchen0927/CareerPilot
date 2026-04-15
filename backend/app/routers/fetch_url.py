import logging
import re

import aiohttp
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright
from pydantic import BaseModel, HttpUrl

router = APIRouter(prefix="/api/jobs", tags=["fetch-url"])
logger = logging.getLogger(__name__)

TIMEOUT_S = 15
TIMEOUT_MS = 15_000
MIN_LENGTH = 50
MAX_LENGTH = 8000

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

# Tags that are pure noise and should be removed before text extraction
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


class FetchUrlRequest(BaseModel):
    url: HttpUrl


def _parse_html(html: str) -> str:
    """Strip noise from HTML and return the main content as plain text."""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    # Prefer semantic main-content containers
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"id": re.compile(r"job|content|detail", re.I)})
        or soup.find(attrs={"class": re.compile(r"job|content|detail|description", re.I)})
        or soup.body
    )

    raw = main.get_text(separator="\n") if main else soup.get_text(separator="\n")

    # Collapse blank lines (keep at most one blank line between paragraphs)
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


async def _fetch_with_aiohttp(url: str) -> str | None:
    """Try to fetch the page with aiohttp + BeautifulSoup. Returns None on failure."""
    try:
        timeout = aiohttp.ClientTimeout(total=TIMEOUT_S)
        async with aiohttp.ClientSession(headers=_HEADERS, timeout=timeout) as session:
            async with session.get(url, ssl=False) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
        return _parse_html(html)
    except Exception as e:
        logger.debug("aiohttp fetch failed for %s: %s", url, e)
        return None


async def _fetch_with_playwright(url: str) -> str:
    """Fallback: launch headless Chromium and extract innerText."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_extra_http_headers({"User-Agent": _HEADERS["User-Agent"]})
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
            await page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)
        except PlaywrightTimeout:
            pass
        html = await page.content()
        await browser.close()
    return _parse_html(html)


@router.post("/fetch-url")
async def fetch_job_url(request: FetchUrlRequest):
    """Fetch a job listing page. Tries aiohttp+BeautifulSoup first; falls back to Playwright."""
    url = str(request.url)

    text = await _fetch_with_aiohttp(url)

    if not text or len(text) < MIN_LENGTH:
        logger.info("aiohttp yielded too little content, falling back to Playwright for %s", url)
        try:
            text = await _fetch_with_playwright(url)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"頁面擷取失敗：{e}") from e

    text = text.strip()
    if len(text) < MIN_LENGTH:
        raise HTTPException(status_code=422, detail="頁面內容太少，可能被阻擋，請改用手動貼上")

    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH]

    return {"text": text}
