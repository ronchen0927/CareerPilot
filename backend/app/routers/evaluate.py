import json

from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI

from ..config import settings
from ..models import JobEvaluateRequest, JobEvaluateResponse

router = APIRouter(prefix="/api/jobs", tags=["evaluate"])


@router.post("/evaluate", response_model=JobEvaluateResponse)
async def evaluate_job(request: JobEvaluateRequest):
    """使用 GPT 評估職缺與求職者的匹配程度"""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="尚未設定 OPENAI_API_KEY，請在 backend/.env 加入 OPENAI_API_KEY=sk-...",
        )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    job = request.job
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

    try:
        response = await client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=600,
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
