import hashlib
import json

from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI

from ..config import settings
from ..db import get_cached, save_evaluation
from ..models import JobEvaluateRequest, JobEvaluateResponse, JobEvaluateTextRequest

router = APIRouter(prefix="/api/jobs", tags=["evaluate"])


def _make_openai_client() -> AsyncOpenAI:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="尚未設定 OPENAI_API_KEY，請在 backend/.env 加入 OPENAI_API_KEY=sk-...",
        )
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def _compute_hash(*parts: str) -> str:
    combined = "\n".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()


async def _call_openai(client: AsyncOpenAI, prompt: str) -> JobEvaluateResponse:
    try:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_completion_tokens=600,
        )
        data = json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API 錯誤：{e}") from e

    return JobEvaluateResponse(
        score=data.get("score", "N/A"),
        summary=data.get("summary", ""),
        match_points=data.get("match_points", []),
        gap_points=data.get("gap_points", []),
        recommendation=data.get("recommendation", ""),
    )


def _row_to_response(row: dict) -> JobEvaluateResponse:
    return JobEvaluateResponse(
        score=row["score"],
        summary=row["summary"],
        match_points=json.loads(row["match_points"]),
        gap_points=json.loads(row["gap_points"]),
        recommendation=row["recommendation"],
        from_cache=True,
    )


@router.post("/evaluate", response_model=JobEvaluateResponse)
async def evaluate_job(request: JobEvaluateRequest):
    """使用 GPT 評估職缺與求職者的匹配程度（結構化職缺資料）"""
    job = request.job
    # Use structured fields as the canonical text for hashing
    job_repr = f"{job.job}|{job.company}|{job.city}|{job.experience}|{job.education}|{job.salary}"
    job_hash = _compute_hash(job_repr, request.user_cv.strip())

    cached = await get_cached(job_hash)
    if cached:
        return _row_to_response(cached)

    client = _make_openai_client()
    cv_section = f"\n\n## 求職者背景\n{request.user_cv.strip()}" if request.user_cv.strip() else ""

    prompt = f"""You are a professional career advisor. Evaluate the fit between the candidate and the job listing below, then respond in strict JSON format.

## Job Listing
- Title: {job.job}
- Company: {job.company}
- City: {job.city}
- Experience required: {job.experience}
- Education required: {job.education}
- Salary: {job.salary}{cv_section}

## Response format (JSON only, no extra text)
{{
  "score": "Letter grade with optional +/- (e.g. A, B+, C-)",
  "summary": "One-sentence verdict in Traditional Chinese, max 25 characters",
  "match_points": ["Up to 3 strengths in Traditional Chinese, max 20 chars each"],
  "gap_points": ["Up to 3 risks or gaps in Traditional Chinese, max 20 chars each — empty array if none"],
  "recommendation": "Application advice in Traditional Chinese, max 50 characters"
}}

All text values must be written in Traditional Chinese (繁體中文).
"""
    result = await _call_openai(client, prompt)
    await save_evaluation(
        job_hash=job_hash,
        job_text=job_repr,
        job_url=job.link or None,
        score=result.score,
        summary=result.summary,
        match_points=result.match_points,
        gap_points=result.gap_points,
        recommendation=result.recommendation,
    )
    return result


@router.post("/evaluate-text", response_model=JobEvaluateResponse)
async def evaluate_job_text(request: JobEvaluateTextRequest):
    """使用 GPT 評估職缺與求職者的匹配程度（純文字職缺描述）"""
    job_hash = _compute_hash(request.job_text.strip(), request.user_cv.strip())

    cached = await get_cached(job_hash)
    if cached:
        return _row_to_response(cached)

    client = _make_openai_client()
    cv_section = f"\n\n## 求職者背景\n{request.user_cv.strip()}" if request.user_cv.strip() else ""

    prompt = f"""You are a professional career advisor. Evaluate the fit between the candidate and the job listing below, then respond in strict JSON format.

## Job Listing (raw description)
{request.job_text.strip()}{cv_section}

## Response format (JSON only, no extra text)
{{
  "score": "Letter grade with optional +/- (e.g. A, B+, C-)",
  "summary": "One-sentence verdict in Traditional Chinese, max 25 characters",
  "match_points": ["Up to 3 strengths in Traditional Chinese, max 20 chars each"],
  "gap_points": ["Up to 3 risks or gaps in Traditional Chinese, max 20 chars each — empty array if none"],
  "recommendation": "Application advice in Traditional Chinese, max 50 characters"
}}

All text values must be written in Traditional Chinese (繁體中文).
"""
    result = await _call_openai(client, prompt)
    await save_evaluation(
        job_hash=job_hash,
        job_text=request.job_text.strip(),
        job_url=None,
        score=result.score,
        summary=result.summary,
        match_points=result.match_points,
        gap_points=result.gap_points,
        recommendation=result.recommendation,
    )
    return result
