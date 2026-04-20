import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from ..fetchers import fetch_104_detail, fetch_with_aiohttp, fetch_with_playwright

router = APIRouter(prefix="/api/jobs", tags=["fetch-url"])
logger = logging.getLogger(__name__)

MIN_LENGTH = 200
MAX_LENGTH = 8000


class FetchUrlRequest(BaseModel):
    url: HttpUrl


@router.post("/fetch-url")
async def fetch_job_url(request: FetchUrlRequest):
    """Fetch job content. For 104 URLs uses the structured API; falls back to scraping."""
    url = str(request.url)

    # 104: structured API is primary — complete and reliable
    text = await fetch_104_detail(url)
    if text:
        return {"text": text[:MAX_LENGTH]}

    # Non-104 (or API failure): scrape with aiohttp → Playwright fallback
    text = await fetch_with_aiohttp(url)
    if not text or len(text) < MIN_LENGTH:
        logger.info("aiohttp yielded too little content, falling back to Playwright for %s", url)
        try:
            text = await fetch_with_playwright(url)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"頁面擷取失敗：{e}") from e

    text = (text or "").strip()
    if len(text) < MIN_LENGTH:
        raise HTTPException(status_code=422, detail="頁面內容太少，可能被阻擋，請改用手動貼上")

    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH]

    return {"text": text}
