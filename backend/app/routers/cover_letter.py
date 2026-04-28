from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI

from ..config import settings
from ..db import delete_cover_letter, get_cover_letter, list_cover_letters, save_cover_letter
from ..models import (
    CoverLetterRecord,
    CoverLetterRequest,
    CoverLetterResponse,
    ExtractCompanyRequest,
    ExtractCompanyResponse,
)

router = APIRouter(tags=["cover-letter"])

_PROMPT = """\
You are a career coach helping a job seeker write a cover letter in Traditional Chinese.

## Instructions
- Write 3–4 natural paragraphs for the body, approximately 250–350 characters total.
- Use first-person, conversational tone — as if the candidate is speaking directly to the hiring manager.
- Do NOT use clichés like "I am writing to express my interest" or overly formal phrases like "貴公司" or "敬啟者".
- Pick 2–3 concrete skills or achievements from the CV that directly match the job requirements.
{greeting_instruction}
{closing_instruction}
- All output must be in Traditional Chinese (繁體中文).

## Job Description
{job_text}

## Candidate Background
{user_cv}
"""

_EXTRACT_COMPANY_PROMPT = """\
Extract the company name from the following job description.
Return ONLY the company name as it appears in the text (Traditional Chinese or English).
If you cannot determine the company name, return an empty string.
Output only the company name, nothing else — no explanation, no punctuation.

Job Description:
{job_text}
"""


def _make_client() -> AsyncOpenAI:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="尚未設定 OPENAI_API_KEY，請在 backend/.env 加入 OPENAI_API_KEY=sk-...",
        )
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


@router.post("/api/jobs/cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter(request: CoverLetterRequest):
    """根據職缺描述與履歷，用 AI 產生自我推薦信並存入資料庫"""
    client = _make_client()
    cv_section = request.user_cv.strip() or "（未提供）"
    company = request.company_name.strip()
    user = request.user_name.strip()

    if company:
        greeting_instruction = (
            f"- Start with a natural, warm greeting addressing the {company} "
            "recruiting team. The phrasing should feel genuine — adapt tone to the company culture, "
            "not formulaic. For example: '親愛的 ACME 招募夥伴：' or '嗨，XXX 團隊：'"
        )
    else:
        greeting_instruction = "- Do not include a salutation header."

    if user:
        closing_instruction = (
            "- End with an appropriate closing phrase that matches the letter's tone "
            "(e.g. 「祝商祺」for startups, 「此致 敬禮」for formal companies, "
            f"「期待有機會加入你們」for casual), then a blank line, then the sender's name: {user}"
        )
    else:
        closing_instruction = "- Do not include a sign-off or signature."

    try:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {
                    "role": "user",
                    "content": _PROMPT.format(
                        greeting_instruction=greeting_instruction,
                        closing_instruction=closing_instruction,
                        job_text=request.job_text.strip()[:5000],
                        user_cv=cv_section,
                    ),
                }
            ],
            temperature=0.7,
            max_completion_tokens=1200,
        )
        letter = (response.choices[0].message.content or "").strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API 錯誤：{e}") from e

    if not letter:
        raise HTTPException(status_code=502, detail="AI 未回傳內容，請稍後再試")

    record_id = await save_cover_letter(job_text=request.job_text.strip(), letter=letter)
    return CoverLetterResponse(id=record_id, letter=letter)


@router.post("/api/jobs/extract-company", response_model=ExtractCompanyResponse)
async def extract_company_name(request: ExtractCompanyRequest):
    """從職缺描述中用 AI 萃取公司名稱"""
    client = _make_client()
    try:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {
                    "role": "user",
                    "content": _EXTRACT_COMPANY_PROMPT.format(
                        job_text=request.job_text.strip()[:3000]
                    ),
                }
            ],
            temperature=0,
            max_completion_tokens=50,
        )
        company_name = (response.choices[0].message.content or "").strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API 錯誤：{e}") from e

    return ExtractCompanyResponse(company_name=company_name)


@router.get("/api/cover-letters", response_model=list[CoverLetterRecord])
async def get_cover_letters():
    """回傳所有推薦信歷史（由新到舊）"""
    rows = await list_cover_letters()
    return [
        CoverLetterRecord(
            id=r["id"],
            job_text_snippet=r["job_text"][:80],
            job_text=r["job_text"],
            letter=r["letter"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.get("/api/cover-letters/{record_id}", response_model=CoverLetterRecord)
async def get_cover_letter_by_id(record_id: int):
    """回傳單筆推薦信"""
    row = await get_cover_letter(record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="找不到此推薦信紀錄")
    return CoverLetterRecord(
        id=row["id"],
        job_text_snippet=row["job_text"][:80],
        job_text=row["job_text"],
        letter=row["letter"],
        created_at=row["created_at"],
    )


@router.delete("/api/cover-letters/{record_id}", status_code=204)
async def remove_cover_letter(record_id: int):
    """刪除指定推薦信"""
    deleted = await delete_cover_letter(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到此推薦信紀錄")
