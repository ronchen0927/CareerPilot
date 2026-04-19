import io
import json

import pdfplumber
from fastapi import APIRouter, HTTPException, UploadFile
from openai import AsyncOpenAI

from ..config import settings
from ..models import CVSuggestKeywordsRequest, CVSuggestKeywordsResponse

router = APIRouter(prefix="/api/cv", tags=["cv"])

MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/parse")
async def parse_cv(file: UploadFile):
    """從上傳的 PDF 履歷中抽取純文字"""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="請上傳 PDF 格式的履歷")

    raw = await file.read()
    if len(raw) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="檔案大小超過 5 MB 限制")

    try:
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages_text).strip()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"PDF 解析失敗：{e}") from e

    if not text:
        raise HTTPException(status_code=422, detail="無法從此 PDF 擷取文字，請確認非掃描圖片格式")

    return {"text": text}


@router.post("/suggest-keywords", response_model=CVSuggestKeywordsResponse)
async def suggest_keywords(request: CVSuggestKeywordsRequest):
    """根據履歷內容，用 AI 建議 3-5 組求職關鍵字"""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="尚未設定 OPENAI_API_KEY，請在 backend/.env 加入 OPENAI_API_KEY=sk-...",
        )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = f"""You are a career advisor. Based on the resume below, suggest 3 to 5 Traditional Chinese job search keywords (職位名稱) that best match the candidate's skills and experience.

## Resume
{request.cv_text.strip()}

## Response format (JSON only, no extra text)
{{
  "keywords": ["關鍵字1", "關鍵字2", "關鍵字3"]
}}

Rules:
- Each keyword is a job title in Traditional Chinese (繁體中文), e.g. "後端工程師", "Python 工程師", "資料工程師"
- Return 3 to 5 keywords
- JSON only, no explanations
"""
    try:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_completion_tokens=200,
        )
        data = json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API 錯誤：{e}") from e

    keywords = data.get("keywords", [])
    if not isinstance(keywords, list):
        keywords = []

    return CVSuggestKeywordsResponse(keywords=keywords)
