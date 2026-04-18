from fastapi import APIRouter
from pydantic import BaseModel

from ..db import get_liveness_map
from ..liveness import check_urls

router = APIRouter(prefix="/api/liveness", tags=["liveness"])


class _UrlListRequest(BaseModel):
    urls: list[str]


@router.post("/status")
async def get_liveness_status(request: _UrlListRequest):
    """回傳指定 URL 清單的活躍狀態（前端傳入 bookmark URL 清單）"""
    result = await get_liveness_map(request.urls)
    return {
        url: {
            "status": row["status"],
            "last_checked": row["last_checked"],
            "reason": row.get("last_reason"),
        }
        for url, row in result.items()
    }


@router.post("/check")
async def trigger_liveness_check(request: _UrlListRequest):
    """立即觸發指定 URL 的活躍狀態檢查（「重新檢查」按鈕使用）"""
    count = await check_urls(request.urls)
    return {"checked": count}
