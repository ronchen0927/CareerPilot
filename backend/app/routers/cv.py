import io

import pdfplumber
from fastapi import APIRouter, HTTPException, UploadFile

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
