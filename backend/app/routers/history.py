import json

from fastapi import APIRouter, HTTPException

from ..db import delete_evaluation, list_evaluations
from ..models import EvaluationRecord

router = APIRouter(prefix="/api/evaluations", tags=["history"])


@router.get("", response_model=list[EvaluationRecord])
async def get_evaluations():
    """回傳所有歷史評分紀錄（由新到舊）"""
    rows = await list_evaluations()
    return [
        EvaluationRecord(
            id=r["id"],
            job_text_snippet=r["job_text"][:80],
            job_url=r["job_url"],
            score=r["score"],
            summary=r["summary"],
            match_points=json.loads(r["match_points"]),
            gap_points=json.loads(r["gap_points"]),
            recommendation=r["recommendation"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.delete("/{record_id}", status_code=204)
async def remove_evaluation(record_id: int):
    """刪除指定評分紀錄"""
    deleted = await delete_evaluation(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到此評分紀錄")
