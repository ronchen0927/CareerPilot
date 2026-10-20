from fastapi import APIRouter, HTTPException

from ..db import (
    insert_applications,
    list_applications,
    unboard_application,
    update_application_status,
)
from ..models import ApplicationIn, ApplicationRecord, ApplicationStatusUpdate

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationRecord])
async def get_applications():
    """回傳所有應徵追蹤紀錄（看板）"""
    return await list_applications()


@router.post("", status_code=204)
async def add_application(item: ApplicationIn):
    """加入看板；url 已在看板上則忽略，不在看板上則放回"""
    await insert_applications([item.model_dump()])


@router.post("/import", status_code=204)
async def import_applications(items: list[ApplicationIn]):
    """一次性匯入（localStorage → SQLite）；規則同新增"""
    await insert_applications([i.model_dump() for i in items])


@router.patch("/status", status_code=204)
async def set_application_status(body: ApplicationStatusUpdate):
    """更新狀態；狀態有變時更新 status_changed_at"""
    if not await update_application_status(body.url, body.status):
        raise HTTPException(status_code=404, detail="找不到此應徵紀錄")


@router.delete("", status_code=204)
async def remove_application(url: str):
    """從看板移除（status 設為 NULL，列保留）"""
    if not await unboard_application(url):
        raise HTTPException(status_code=404, detail="找不到此應徵紀錄")
