import json

from fastapi import APIRouter, HTTPException

from ..db import delete_evaluation, get_evaluation, list_evaluations
from ..models import EvaluationDimensions, EvaluationRecord

router = APIRouter(prefix="/api/evaluations", tags=["history"])


def _to_record(r: dict) -> EvaluationRecord:
    dimensions: EvaluationDimensions | None = None
    if r.get("dimensions"):
        try:
            dimensions = EvaluationDimensions(**json.loads(r["dimensions"]))
        except Exception:
            pass
    return EvaluationRecord(
        id=r["id"],
        job_text_snippet=r["job_text"][:80],
        job_text=r["job_text"],
        job_url=r["job_url"],
        score=r["score"],
        summary=r["summary"],
        match_points=json.loads(r["match_points"]),
        gap_points=json.loads(r["gap_points"]),
        recommendation=r["recommendation"],
        created_at=r["created_at"],
        dimensions=dimensions,
    )


@router.get("", response_model=list[EvaluationRecord])
async def get_evaluations():
    """回傳所有歷史評分紀錄（由新到舊）"""
    rows = await list_evaluations()
    return [_to_record(r) for r in rows]


@router.get("/{record_id}", response_model=EvaluationRecord)
async def get_evaluation_by_id(record_id: int):
    """回傳單筆評分紀錄"""
    row = await get_evaluation(record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="找不到此評分紀錄")
    return _to_record(row)


@router.delete("/{record_id}", status_code=204)
async def remove_evaluation(record_id: int):
    """刪除指定評分紀錄"""
    deleted = await delete_evaluation(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到此評分紀錄")
