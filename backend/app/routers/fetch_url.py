from fastapi import APIRouter, HTTPException
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright
from pydantic import BaseModel, HttpUrl

router = APIRouter(prefix="/api/jobs", tags=["fetch-url"])

TIMEOUT_MS = 15_000


class FetchUrlRequest(BaseModel):
    url: HttpUrl


@router.post("/fetch-url")
async def fetch_job_url(request: FetchUrlRequest):
    """用 Playwright 抓取職缺頁面內容，回傳純文字"""
    url = str(request.url)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers(
                {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                }
            )
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                await page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)
            except PlaywrightTimeout:
                # 頁面逾時但可能已有足夠內容，繼續嘗試抽文字
                pass

            text = await page.evaluate("() => document.body?.innerText ?? ''")
            await browser.close()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"頁面擷取失敗：{e}") from e

    text = text.strip()
    if len(text) < 50:
        raise HTTPException(status_code=422, detail="頁面內容太少，可能被阻擋，請改用手動貼上")

    # 截斷過長內容，避免超出 AI token 限制
    if len(text) > 8000:
        text = text[:8000]

    return {"text": text}
