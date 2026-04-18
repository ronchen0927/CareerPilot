import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from ..fetchers import fetch_with_aiohttp, fetch_with_playwright

router = APIRouter(prefix="/api/jobs", tags=["fetch-url"])
logger = logging.getLogger(__name__)

MIN_LENGTH = 50
MAX_LENGTH = 8000


class FetchUrlRequest(BaseModel):
    url: HttpUrl


@router.post("/fetch-url")
async def fetch_job_url(request: FetchUrlRequest):
    """Fetch a job listing page. Tries aiohttp+BeautifulSoup first; falls back to Playwright."""
    url = str(request.url)

    text = await fetch_with_aiohttp(url)

    if not text or len(text) < MIN_LENGTH:
        logger.info("aiohttp yielded too little content, falling back to Playwright for %s", url)
        try:
            text = await fetch_with_playwright(url)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"頁面擷取失敗：{e}") from e

    text = text.strip()
    if len(text) < MIN_LENGTH:
        raise HTTPException(status_code=422, detail="頁面內容太少，可能被阻擋，請改用手動貼上")

    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH]

    return {"text": text}
