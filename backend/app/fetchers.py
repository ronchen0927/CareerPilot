"""Shared HTTP fetch helpers used by the URL-fetch endpoint and the liveness checker."""

import html
import json
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


_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.DOTALL
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(raw: str) -> str:
    text = _HTML_TAG_RE.sub("", raw)
    return html.unescape(text).strip()


def _extract_cake_next_data(raw_html: str) -> str:
    """Parse __NEXT_DATA__ from a CakeResume job page and return formatted plain text."""
    m = _NEXT_DATA_RE.search(raw_html)
    if not m:
        return ""
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return ""

    job = data.get("props", {}).get("pageProps", {}).get("job")
    if not job:
        return ""

    lines: list[str] = []

    title = job.get("title", "")
    if title:
        lines.append(f"職位：{title}")

    locations = job.get("locations") or []
    loc_names = [loc.get("full_name", "") for loc in locations if loc.get("full_name")]
    if loc_names:
        lines.append(f"地點：{', '.join(loc_names)}")

    remote = job.get("remote", "")
    if remote and remote != "no_remote_work":
        lines.append(f"遠端：{remote}")

    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    salary_type = job.get("salary_type", "")
    if salary_min or salary_max:
        salary_str = f"{int(float(salary_min)):,}" if salary_min else "?"
        if salary_max:
            salary_str += f" ~ {int(float(salary_max)):,}"
        lines.append(f"薪資（{salary_type}）：{salary_str}")

    job_type = job.get("job_type", "")
    if job_type:
        lines.append(f"工作類型：{job_type}")

    seniority = job.get("seniority_level", "")
    if seniority:
        lines.append(f"資歷：{seniority}")

    description = _strip_html(job.get("description") or "")
    if description:
        lines.append(f"\n【工作內容】\n{description}")

    requirements = _strip_html(job.get("requirements") or "")
    if requirements:
        lines.append(f"\n【職位要求】\n{requirements}")

    return "\n".join(lines)


async def fetch_cake_detail(url: str) -> str:
    """Fetch CakeResume job detail by extracting __NEXT_DATA__ SSR JSON.

    Tries aiohttp first (faster); falls back to Playwright if the page requires JS.
    """
    if not _CAKE_JOB_RE.match(url):
        return ""

    # Fast path: __NEXT_DATA__ is server-rendered, no JS execution needed
    try:
        timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT_S)
        async with aiohttp.ClientSession(headers=_HEADERS, timeout=timeout) as session:
            async with session.get(url, ssl=False) as resp:
                if resp.status == 200:
                    raw = await resp.text()
                    text = _extract_cake_next_data(raw)
                    if text:
                        return text
    except Exception as e:
        logger.debug("CakeResume aiohttp fetch failed for %s: %s", url, e)

    # Slow path: render with Playwright and re-extract
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_extra_http_headers({"User-Agent": _HEADERS["User-Agent"]})
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=FETCH_TIMEOUT_MS)
            raw = await page.content()
            return _extract_cake_next_data(raw)
        except Exception as e:
            logger.debug("CakeResume Playwright fetch failed for %s: %s", url, e)
            return ""
        finally:
            await browser.close()
