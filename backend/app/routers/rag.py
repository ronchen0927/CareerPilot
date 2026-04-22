import json
import math
import traceback

from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI

from ..config import settings
from ..db import delete_rag_document, list_rag_documents, save_rag_document
from ..models import (
    MockInterviewRequest,
    MockInterviewResponse,
    RagDocumentCreate,
    RagDocumentResponse,
    ResumeMatchRequest,
    ResumeMatchResponse,
)

router = APIRouter(prefix="/api/rag", tags=["RAG"])


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(v1, v2, strict=True))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(b * b for b in v2))
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)


def _make_openai_client() -> AsyncOpenAI:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is missing")
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def _get_embedding(client: AsyncOpenAI, text: str) -> list[float]:
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


async def _retrieve_top_k(
    target_embedding: list[float], doc_types: list[str], top_k: int = 5
) -> list[dict]:
    all_docs = []
    for dt in doc_types:
        all_docs.extend(await list_rag_documents(doc_type=dt))

    for doc in all_docs:
        doc_emb = json.loads(doc["embedding"])
        doc["score"] = cosine_similarity(target_embedding, doc_emb)

    all_docs.sort(key=lambda x: x["score"], reverse=True)
    return all_docs[:top_k]


@router.post("/documents", response_model=RagDocumentResponse)
async def create_document(req: RagDocumentCreate):
    client = _make_openai_client()
    try:
        embedding = await _get_embedding(client, req.content)
        doc_id = await save_rag_document(req.doc_type, req.content, embedding)
        docs = await list_rag_documents(doc_type=req.doc_type)
        for doc in docs:
            if doc["id"] == doc_id:
                return RagDocumentResponse(
                    id=doc["id"],
                    doc_type=doc["doc_type"],
                    content=doc["content"],
                    created_at=doc["created_at"],
                )
        raise HTTPException(status_code=500, detail="Failed to retrieve saved document")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/documents", response_model=list[RagDocumentResponse])
async def get_documents(doc_type: str | None = None):
    docs = await list_rag_documents(doc_type=doc_type)
    return [RagDocumentResponse(**doc) for doc in docs]


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int):
    success = await delete_rag_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "deleted"}


@router.post("/mock-interview", response_model=MockInterviewResponse)
async def generate_mock_interview(req: MockInterviewRequest):
    client = _make_openai_client()
    jd_embedding = await _get_embedding(client, req.job_text)

    retrieved_docs = await _retrieve_top_k(jd_embedding, ["project", "interview_question"], top_k=5)
    context_text = "\n\n".join([f"[{d['doc_type']}] {d['content']}" for d in retrieved_docs])

    system_prompt = """你是一個專業的技術面試官與職涯教練。
你的任務是根據提供的「目標職缺描述 (JD)」以及候選人的「個人專案/歷史面試題庫 (Context)」，
動態生成高相關性的技術與行為面試題。
請務必以 JSON 格式回覆，包含以下欄位：
- technical_questions: 字串陣列，包含 3-5 個技術面試問題。
- behavioral_questions: 字串陣列，包含 3-5 個行為面試問題。
- tips: 字串，面試準備的綜合建議。"""

    user_prompt = f"【職缺描述】\n{req.job_text}\n\n【參考資料 (專案與歷史題)】\n{context_text}"

    try:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_completion_tokens=900,
        )
        data = json.loads(response.choices[0].message.content or "{}")
        return MockInterviewResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API 錯誤：{e}") from e


@router.post("/resume-match", response_model=ResumeMatchResponse)
async def generate_resume_match(req: ResumeMatchRequest):
    client = _make_openai_client()
    jd_embedding = await _get_embedding(client, req.job_text)

    retrieved_docs = await _retrieve_top_k(jd_embedding, ["experience", "project"], top_k=5)
    context_text = "\n\n".join([f"[{d['doc_type']}] {d['content']}" for d in retrieved_docs])

    system_prompt = """你是一個資深的後端/AI架構師與技術招募專家。
請比對候選人的「過往經驗與專案 (Context)」及「履歷 (CV)」與「目標職缺 (JD)」的契合度。
精準比對個人後端架構與 AI 應用開發經驗與特定職缺的要求。
請以 JSON 格式回覆，包含以下欄位：
- gap_analysis: 字串，能力缺口分析。
- answer_strategy: 字串，彌補缺口或突顯優勢的答題策略。
- match_score: 數字 (0-100)，代表整體契合度。"""

    user_prompt = f"【職缺描述】\n{req.job_text}\n\n【候選人履歷】\n{req.user_cv}\n\n【檢索到的相關經驗與專案】\n{context_text}"

    try:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_completion_tokens=900,
        )
        data = json.loads(response.choices[0].message.content or "{}")
        return ResumeMatchResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API 錯誤：{e}") from e
