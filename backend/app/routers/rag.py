import json
import math
import traceback

from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI

from ..config import settings
from ..db import delete_rag_document, list_rag_documents, save_rag_document
from ..models import (
    CVExtractRequest,
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


@router.post("/extract-cv")
async def extract_cv_to_documents(req: CVExtractRequest):
    client = _make_openai_client()
    system_prompt = """You are an expert resume parser.
Extract individual distinct "projects" and "work experiences" from the provided resume text.
For each item, provide a detailed textual description that encapsulates the skills, tech stack, and achievements.
Respond strictly in JSON format with a single key 'items' containing a list of objects.
Each object must have:
- 'doc_type': either 'project' or 'experience'.
- 'content': a detailed paragraph describing it."""
    try:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.cv_text},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_completion_tokens=1500,
        )
        data = json.loads(response.choices[0].message.content or "{}")
        items = data.get("items", [])

        saved_count = 0
        for item in items:
            doc_type = item.get("doc_type")
            content = item.get("content")
            if doc_type in ["project", "experience"] and content:
                emb = await _get_embedding(client, content)
                await save_rag_document(doc_type, content, emb)
                saved_count += 1

        return {
            "message": f"Successfully extracted and saved {saved_count} documents.",
            "count": saved_count,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"OpenAI API 錯誤：{e}") from e


@router.post("/mock-interview", response_model=MockInterviewResponse)
async def generate_mock_interview(req: MockInterviewRequest):
    client = _make_openai_client()
    jd_embedding = await _get_embedding(client, req.job_text)

    retrieved_docs = await _retrieve_top_k(jd_embedding, ["project", "interview_question"], top_k=5)
    context_text = "\n\n".join([f"[{d['doc_type']}] {d['content']}" for d in retrieved_docs])

    system_prompt = """You are a professional technical interviewer and career coach.
Your task is to dynamically generate highly relevant technical and behavioral interview questions based on the provided "Target Job Description (JD)" and the candidate's "Personal Projects/Historical Interview Questions (Context)".
Please respond in strict JSON format with the following fields:
- technical_questions: Array of strings, containing 3-5 technical interview questions.
- behavioral_questions: Array of strings, containing 3-5 behavioral interview questions.
- tips: String, comprehensive advice for interview preparation.

All text values must be written in Traditional Chinese (繁體中文)."""

    user_prompt = f"## Target Job Description (JD)\n{req.job_text}\n\n## Reference Material (Projects & History)\n{context_text}"

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

    system_prompt = """You are a senior backend/AI architect and technical recruiting expert.
Evaluate the fit between the candidate's "Past Experience and Projects (Context)", "Resume (CV)", and the "Target Job Description (JD)".
Accurately match the candidate's backend architecture and AI application development experience with the specific requirements of the job.
Please respond in strict JSON format with the following fields:
- gap_analysis: String, capability gap analysis.
- answer_strategy: String, answering strategy to bridge gaps or highlight strengths.
- match_score: Number (0-100), representing the overall match percentage.

All text values must be written in Traditional Chinese (繁體中文)."""

    user_prompt = f"## Target Job Description (JD)\n{req.job_text}\n\n## Candidate Resume (CV)\n{req.user_cv}\n\n## Retrieved Relevant Experience and Projects\n{context_text}"

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
