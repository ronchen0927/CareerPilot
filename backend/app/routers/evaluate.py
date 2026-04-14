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

    prompt = f"""你是一個專業的求職顧問，請評估以下職缺的匹配程度並以 JSON 格式回應。

## 職缺資訊
- 職位：{job.job}
- 公司：{job.company}
- 城市：{job.city}
- 經歷要求：{job.experience}
- 最低學歷：{job.education}
- 薪水：{job.salary}{cv_section}

請用繁體中文，以 JSON 格式回應以下欄位：
- "score": 評分字串，格式為字母加減號（如 "A", "B+", "C-", "D"）
- "summary": 一句話總結，25 字以內
- "match_points": 優勢或符合點，字串陣列，最多 3 點，每點 20 字以內
- "gap_points": 落差或風險，字串陣列，最多 3 點，每點 20 字以內（若無明顯落差可為空陣列）
- "recommendation": 投遞建議，50 字以內
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
