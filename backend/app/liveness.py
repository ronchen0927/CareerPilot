"""Background liveness checker: periodically verifies that evaluated job URLs are still live."""

import asyncio
import logging

from .db import get_liveness_fail_count, list_liveness_targets, upsert_liveness
from .fetchers import fetch_with_aiohttp

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 6 * 3600
_DEBOUNCE_THRESHOLD = 2

_DEAD_KEYWORDS = [
    "職缺已關閉",
    "此職缺已結束",
    "職缺不存在",
    "找不到此職缺",
    "no longer available",
    "not accepting applications",
    "job has been closed",
    "this position has been filled",
]


async def run_liveness_loop() -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        try:
            await _check_all()
        except Exception as e:
            logger.error("liveness cycle error: %s", e)


async def _check_url(url: str) -> tuple[str, str]:
    """Return (status, reason) for a single URL. Does NOT use Playwright fallback."""
    text = await fetch_with_aiohttp(url)
    if text is None:
        return "dead", "http_error"
    if any(kw in text for kw in _DEAD_KEYWORDS):
        return "dead", "closed_keyword"
    if len(text) < 200:
        return "unknown", "too_short"
    return "alive", "ok"


async def _check_all() -> None:
    urls = await list_liveness_targets()
    if not urls:
        return
    logger.info("liveness check: %d URLs to verify", len(urls))
    for url in urls:
        try:
            await _check_and_persist(url)
        except Exception as e:
            logger.error("liveness check failed for %s: %s", url, e)


async def _check_and_persist(url: str) -> None:
    status, reason = await _check_url(url)
    if status == "dead":
        fail_count = await get_liveness_fail_count(url) + 1
        if fail_count < _DEBOUNCE_THRESHOLD:
            status = "unknown"
        await upsert_liveness(url, status, reason, fail_count)
    else:
        await upsert_liveness(url, status, reason, 0)


async def check_urls(urls: list[str]) -> int:
    """Immediately re-check a specific set of URLs (triggered via API)."""
    count = 0
    for url in urls:
        try:
            await _check_and_persist(url)
            count += 1
        except Exception as e:
            logger.error("immediate liveness check failed for %s: %s", url, e)
    return count
