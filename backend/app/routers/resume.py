import json

from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI

from ..config import settings
from ..db import (
    delete_resume_rewrite,
    get_resume_rewrite,
    list_resume_rewrites,
    save_resume_rewrite,
)
from ..models import (
    ResumeRewriteRecord,
    ResumeRewriteRequest,
    ResumeRewriteResponse,
    ResumeStructured,
)

router = APIRouter(tags=["resume-rewrite"])

_PLAIN_PROMPT = """\
You are a professional career coach helping a job seeker tailor their resume to a specific job opening.

## Task
Rewrite the candidate's resume to best fit the job description below. Emphasize the experience, skills, and achievements that directly match the requirements. Keep all factual claims from the original resume — do NOT invent new experience. Reorder and reword content for maximum relevance.

## Style
- Output one cohesive plain-text resume in Traditional Chinese (繁體中文).
- Keep it concise (roughly 400–700 characters).
- Use natural section headings (自我介紹 / 工作經歷 / 技能 / 等) as plain text, separated by blank lines.
- Do NOT use Markdown syntax (no #, *, -, backticks). Use plain text with blank lines for spacing.
- No preamble, no explanation, no closing commentary — output the resume content only.

## Job Description
{job_text}

## Original Resume
{user_cv}
"""

_STRUCTURED_PROMPT = """\
You are a professional career coach helping a job seeker tailor their resume to a specific job opening.

## Task
Rewrite the candidate's resume to best fit the job description below. Emphasize the experience, skills, and achievements that directly match the requirements. Keep all factual claims from the original resume — do NOT invent new experience.

## Output Format
Respond with strict JSON only — no extra text, no markdown code fences.
{{
  "summary": "自我介紹段落，100–150 字，強調與此職位最相關的定位與價值。繁體中文。",
  "experience": [
    "條列 3–5 則工作經歷，每則一句話，聚焦於符合 JD 需求的成果（動詞開頭、含量化數字更佳）。繁體中文。"
  ],
  "skills": [
    "條列 5–10 項最能對應 JD 的技能關鍵字。繁體中文或原文專有名詞皆可。"
  ]
}}

All output values must be in Traditional Chinese (繁體中文), except widely-used technical terms (e.g. Python, FastAPI) which may stay in English.

## Job Description
{job_text}

## Original Resume
{user_cv}
"""


def _make_client() -> AsyncOpenAI:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="尚未設定 OPENAI_API_KEY，請在 backend/.env 加入 OPENAI_API_KEY=sk-...",
        )
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def _call_plain(client: AsyncOpenAI, job_text: str, user_cv: str) -> str:
    try:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {
                    "role": "user",
                    "content": _PLAIN_PROMPT.format(job_text=job_text, user_cv=user_cv),
                }
            ],
            temperature=0.6,
            max_completion_tokens=1800,
        )
        text = (response.choices[0].message.content or "").strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API 錯誤：{e}") from e

    if not text:
        raise HTTPException(status_code=502, detail="AI 未回傳內容，請稍後再試")
    return text


async def _call_structured(client: AsyncOpenAI, job_text: str, user_cv: str) -> ResumeStructured:
    try:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {
                    "role": "user",
                    "content": _STRUCTURED_PROMPT.format(job_text=job_text, user_cv=user_cv),
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.6,
            max_completion_tokens=1800,
        )
        data = json.loads(response.choices[0].message.content or "{}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API 錯誤：{e}") from e

    summary = (data.get("summary") or "").strip()
    if not summary:
        raise HTTPException(status_code=502, detail="AI 未回傳內容，請稍後再試")

    return ResumeStructured(
        summary=summary,
        experience=data.get("experience") or [],
        skills=data.get("skills") or [],
    )


def _row_to_record(row: dict) -> ResumeRewriteRecord:
    mode = row["mode"]
    plain_result: str | None = None
    structured_result: ResumeStructured | None = None
    if mode == "structured":
        try:
            parsed = json.loads(row["result"])
            structured_result = ResumeStructured(
                summary=parsed.get("summary", ""),
                experience=parsed.get("experience", []),
                skills=parsed.get("skills", []),
            )
        except json.JSONDecodeError:
            plain_result = row["result"]
    else:
        plain_result = row["result"]

    return ResumeRewriteRecord(
        id=row["id"],
        job_text_snippet=row["job_text"][:80],
        job_text=row["job_text"],
        job_url=row["job_url"],
        original_cv=row["original_cv"],
        mode=mode,
        plain_result=plain_result,
        structured_result=structured_result,
        created_at=row["created_at"],
    )


@router.post("/api/jobs/resume-rewrite", response_model=ResumeRewriteResponse)
async def rewrite_resume(request: ResumeRewriteRequest):
    """根據職缺描述改寫履歷，支援 plain / structured 兩種模式"""
    if request.mode not in ("plain", "structured"):
        raise HTTPException(status_code=422, detail="mode 必須為 'plain' 或 'structured'")

    client = _make_client()
    job_text = request.job_text.strip()
    user_cv = request.user_cv.strip()

    if request.mode == "plain":
        plain_text = await _call_plain(client, job_text, user_cv)
        record_id = await save_resume_rewrite(
            job_text=job_text,
            job_url=request.job_url,
            original_cv=user_cv,
            mode="plain",
            result=plain_text,
        )
        return ResumeRewriteResponse(id=record_id, mode="plain", plain_result=plain_text)

    structured = await _call_structured(client, job_text, user_cv)
    record_id = await save_resume_rewrite(
        job_text=job_text,
        job_url=request.job_url,
        original_cv=user_cv,
        mode="structured",
        result=structured.model_dump_json(),
    )
    return ResumeRewriteResponse(id=record_id, mode="structured", structured_result=structured)


@router.get("/api/resume-rewrites", response_model=list[ResumeRewriteRecord])
async def get_resume_rewrites():
    """回傳所有履歷改寫歷史（由新到舊）"""
    rows = await list_resume_rewrites()
    return [_row_to_record(r) for r in rows]


@router.get("/api/resume-rewrites/{record_id}", response_model=ResumeRewriteRecord)
async def get_resume_rewrite_by_id(record_id: int):
    """回傳單筆履歷改寫紀錄"""
    row = await get_resume_rewrite(record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="找不到此履歷改寫紀錄")
    return _row_to_record(row)


@router.delete("/api/resume-rewrites/{record_id}", status_code=204)
async def remove_resume_rewrite(record_id: int):
    """刪除指定履歷改寫紀錄"""
    deleted = await delete_resume_rewrite(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到此履歷改寫紀錄")
