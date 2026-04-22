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
_104_JOB_RE = re.compile(r"https?://(?:www\.)?104\.com\.tw/job/([a-z0-9]+)", re.IGNORECASE)
_CAKE_JOB_RE = re.compile(
    r"https?://(?:www\.)?cake\.me/(?:companies/[^/]+/)?jobs/([^/]+)", re.IGNORECASE
)

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


def _format_104_data(data: dict) -> str:
    """Format 104 API response into plain text for AI context."""
    job_detail = data.get("jobDetail", {})
    condition = data.get("condition", {})
    welfare = data.get("welfare", {})

    lines: list[str] = []

    # Location
    region = job_detail.get("addressRegion") or ""
    addr_detail = job_detail.get("addressDetail") or ""
    address = f"{region}{addr_detail}".strip()
    landmark = job_detail.get("landmark") or ""
    if address:
        loc = f"上班地點：{address}"
        if landmark:
            loc += f"（{landmark}）"
        lines.append(loc)

    # Work conditions
    remote = job_detail.get("remoteWork")
    if isinstance(remote, dict):
        desc = (remote.get("description") or "").strip()
        if not desc:
            _REMOTE_TYPE = {1: "可遠端", 2: "完全遠端"}
            desc = _REMOTE_TYPE.get(remote.get("type", 0), "")
        if desc:
            lines.append(f"遠端工作：{desc}")
    elif remote:
        lines.append(f"遠端工作：{remote}")

    for label, key in [
        ("出差外派", "businessTrip"),
        ("管理職責", "manageResp"),
        ("假期制度", "vacationPolicy"),
        ("招募人數", "needEmp"),
        ("到職時間", "startWorkingDay"),
    ]:
        val = job_detail.get(key)
        if val:
            lines.append(f"{label}：{val}")

    # Skills
    specialties = [s["description"] for s in condition.get("specialty", []) if s.get("description")]
    if specialties:
        lines.append(f"技能要求：{', '.join(specialties)}")

    for lang in condition.get("language", []):
        name = lang.get("language", "")
        ability = lang.get("ability", {})
        if name and ability:
            desc = "、".join(f"{k}{v}" for k, v in ability.items() if v)
            lines.append(f"{name}能力：{desc}")

    # Job description
    job_desc = (job_detail.get("jobDescription") or "").strip()
    if job_desc:
        lines.append(f"\n【工作內容】\n{job_desc}")

    # Welfare
    welfare_tags = welfare.get("tag") or []
    if welfare_tags:
        lines.append(f"福利標籤：{', '.join(welfare_tags)}")
    welfare_text = (welfare.get("welfare") or "").strip()
    if welfare_text:
        lines.append(f"\n【福利制度】\n{welfare_text}")

    return "\n".join(lines)


async def fetch_104_detail(url: str) -> str:
    """Fetch comprehensive job info from 104's detail API. Returns formatted text or ''."""
    m = _104_JOB_RE.match(url)
    if not m:
        return ""
    job_id = m.group(1)
    api_url = f"https://www.104.com.tw/job/ajax/content/{job_id}"
    try:
        timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT_S)
        headers = {**_HEADERS, "Referer": url}
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(api_url, ssl=False) as resp:
                if resp.status != 200:
                    return ""
                data = await resp.json()
        return _format_104_data(data.get("data", {}))
    except Exception as e:
        logger.debug("104 detail API failed for %s: %s", url, e)
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


async def fetch_cake_detail(url: str) -> str:
    """Fetch CakeResume job detail directly using Playwright without trafilatura/Goose3."""
    m = _CAKE_JOB_RE.match(url)
    if not m:
        return ""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_extra_http_headers({"User-Agent": _HEADERS["User-Agent"]})
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=FETCH_TIMEOUT_MS)
            # Wait for any of the common CakeResume description containers
            try:
                await page.wait_for_selector(
                    "div.job-description-content, div[data-testid='job-description'], article, main",
                    timeout=5000,
                )
            except PlaywrightTimeout:
                pass

            text = await page.evaluate("""() => {
                let el = document.querySelector('div[data-testid="job-description"]');
                if (!el) el = document.querySelector('.job-description-content');
                if (!el) el = document.querySelector('article');
                if (!el) el = document.querySelector('main');
                return el ? el.innerText : '';
            }""")
            return (text or "").strip()
        except Exception as e:
            logger.debug("CakeResume detail fetch failed for %s: %s", url, e)
            return ""
        finally:
            await browser.close()
