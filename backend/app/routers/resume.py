from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI

from ..config import settings
from ..db import (
    delete_resume_rewrite,
    get_resume_rewrite,
    list_resume_rewrites,
    save_resume_rewrite,
)
from ..models import ResumeRewriteRecord, ResumeRewriteRequest, ResumeRewriteResponse

router = APIRouter(tags=["resume-rewrite"])

_PROMPT = """\
You are a professional career coach helping a job seeker tailor their resume to a specific job opening.

## Task
Rewrite the candidate's resume to best fit the job description below. Emphasize the experience, skills, and achievements that directly match the requirements. Keep all factual claims from the original resume — do NOT invent new experience. Reorder and reword content for maximum relevance.

## Output Language
Detect the primary language of the ORIGINAL RESUME and write the rewritten resume in the SAME language.
- If the original resume is primarily in Traditional Chinese (繁體中文), write the output in Traditional Chinese.
- If the original resume is primarily in English, write the output in English.
- If the original resume mixes languages, use the dominant language and keep widely-used technical terms in their original form (e.g. Python, FastAPI, PostgreSQL).
- Do NOT translate the resume into a different language than the original.

## Style
- Output one cohesive plain-text resume.
- Keep it concise (roughly 400–700 characters for Chinese, or 250–400 words for English).
- Use natural section headings appropriate to the output language (e.g. 自我介紹 / 工作經歷 / 技能, or Summary / Experience / Skills) as plain text, separated by blank lines.
- Do NOT use Markdown syntax (no #, *, -, backticks). Use plain text with blank lines for spacing.
- No preamble, no explanation, no closing commentary — output the resume content only.

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


async def _call_openai(client: AsyncOpenAI, job_text: str, user_cv: str) -> str:
    try:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {
                    "role": "user",
                    "content": _PROMPT.format(job_text=job_text, user_cv=user_cv),
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


def _row_to_record(row: dict) -> ResumeRewriteRecord:
    return ResumeRewriteRecord(
        id=row["id"],
        job_text_snippet=row["job_text"][:80],
        job_text=row["job_text"],
        job_url=row["job_url"],
        original_cv=row["original_cv"],
        result=row["result"],
        created_at=row["created_at"],
    )


@router.post("/api/jobs/resume-rewrite", response_model=ResumeRewriteResponse)
async def rewrite_resume(request: ResumeRewriteRequest):
    """根據職缺描述改寫履歷。輸出語言跟隨原始履歷（中文 → 中文、英文 → 英文）"""
    client = _make_client()
    job_text = request.job_text.strip()
    user_cv = request.user_cv.strip()

    rewritten = await _call_openai(client, job_text, user_cv)
    record_id = await save_resume_rewrite(
        job_text=job_text,
        job_url=request.job_url,
        original_cv=user_cv,
        result=rewritten,
    )
    return ResumeRewriteResponse(id=record_id, result=rewritten)


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
