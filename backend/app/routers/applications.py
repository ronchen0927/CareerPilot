from fastapi import APIRouter, HTTPException

from ..db import (
    delete_application,
    insert_applications,
    list_applications,
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
    """加入看板；url 已存在則忽略"""
    await insert_applications([item.model_dump()])


@router.post("/import", status_code=204)
async def import_applications(items: list[ApplicationIn]):
    """一次性匯入（localStorage → SQLite）；重複 url 忽略"""
    await insert_applications([i.model_dump() for i in items])


@router.patch("/status", status_code=204)
async def set_application_status(body: ApplicationStatusUpdate):
    """更新狀態；狀態有變時更新 status_changed_at"""
    if not await update_application_status(body.url, body.status):
        raise HTTPException(status_code=404, detail="找不到此應徵紀錄")


@router.delete("", status_code=204)
async def remove_application(url: str):
    """刪除指定 url 的應徵紀錄"""
    if not await delete_application(url):
        raise HTTPException(status_code=404, detail="找不到此應徵紀錄")
