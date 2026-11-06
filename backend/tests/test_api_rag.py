"""Tests for /api/rag endpoints against a temp SQLite DB, OpenAI mocked.

Every embedding call returns JD_VEC, so retrieval order is decided by the
vectors we seed: the doc pointing along JD_VEC must rank first.
"""

import asyncio
import json
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from app import db

JD_VEC = [1.0, 0.0]
JOB_TEXT = "AI 工程師，熟悉 RAG 與向量檢索"


def _make_mock_ai(chat_content: str | None = None, chat_error: Exception | None = None):
    inst = MagicMock()
    emb = MagicMock()
    emb.data[0].embedding = JD_VEC
    inst.embeddings.create = AsyncMock(return_value=emb)
    resp = MagicMock()
    resp.choices[0].message.content = chat_content
    inst.chat.completions.create = AsyncMock(return_value=resp, side_effect=chat_error)
    return inst


@contextmanager
def _openai(inst, key: str = "sk-test"):
    with (
        patch("app.openai_client.settings") as mock_settings,
        patch("app.openai_client.AsyncOpenAI", return_value=inst),
    ):
        mock_settings.OPENAI_API_KEY = key
        yield


def _seed_rag_doc(doc_type: str, content: str, vec: list[float]) -> int:
    return asyncio.run(db.save_rag_document(doc_type, content, vec))


# ── documents ────────────────────────────────────────────────────────────────


def test_create_document_then_list_and_delete(client):
    with _openai(_make_mock_ai()):
        resp = client.post(
            "/api/rag/documents", json={"doc_type": "project", "content": "用 FastAPI 做 RAG 系統"}
        )
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["doc_type"] == "project"
    assert doc["content"] == "用 FastAPI 做 RAG 系統"

    assert [d["id"] for d in client.get("/api/rag/documents?doc_type=project").json()] == [
        doc["id"]
    ]
    assert client.get("/api/rag/documents?doc_type=experience").json() == []

    assert client.delete(f"/api/rag/documents/{doc['id']}").status_code == 204
    assert client.get("/api/rag/documents").json() == []


def test_create_document_missing_key_returns_503(client):
    with _openai(_make_mock_ai(), key=""):
        resp = client.post(
            "/api/rag/documents", json={"doc_type": "project", "content": "用 FastAPI 做 RAG 系統"}
        )
    assert resp.status_code == 503


def test_delete_missing_document_returns_404(client):
    assert client.delete("/api/rag/documents/999").status_code == 404


# ── extract-cv ───────────────────────────────────────────────────────────────


def test_extract_cv_saves_only_valid_items(client):
    items = [
        {"doc_type": "project", "content": "專案 A"},
        {"doc_type": "experience", "content": "經歷 B"},
        {"doc_type": "other", "content": "不該存"},
        {"doc_type": "project", "content": ""},
    ]
    with _openai(_make_mock_ai(json.dumps({"items": items}))):
        resp = client.post("/api/rag/extract-cv", json={"cv_text": "我的履歷"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 2
    assert sorted(d["content"] for d in client.get("/api/rag/documents").json()) == [
        "專案 A",
        "經歷 B",
    ]


def test_extract_cv_openai_error_returns_502(client):
    with _openai(_make_mock_ai(chat_error=Exception("rate limit"))):
        resp = client.post("/api/rag/extract-cv", json={"cv_text": "我的履歷"})
    assert resp.status_code == 502


# ── mock-interview ───────────────────────────────────────────────────────────


def test_mock_interview_uses_closest_docs_and_persists(client):
    _seed_rag_doc("project", "較不相關的專案", [0.0, 1.0])
    _seed_rag_doc("interview_question", "最相關的面試題", [1.0, 0.0])
    _seed_rag_doc("experience", "經歷不屬於面試檢索範圍", [1.0, 0.0])
    reply = {"technical_questions": ["Q1"], "behavioral_questions": ["B1"], "tips": "多練習"}
    with _openai(_make_mock_ai(json.dumps(reply, ensure_ascii=False))):
        resp = client.post("/api/rag/mock-interview", json={"job_text": JOB_TEXT})
    assert resp.status_code == 200
    data = resp.json()
    assert data["used_contexts"] == ["最相關的面試題", "較不相關的專案"]
    assert data["technical_questions"] == ["Q1"]

    [listed] = client.get("/api/rag/mock-interviews").json()
    assert listed["id"] == data["id"]
    detail = client.get(f"/api/rag/mock-interviews/{data['id']}").json()
    assert detail["technical_questions"] == ["Q1"]
    assert detail["behavioral_questions"] == ["B1"]

    assert client.delete(f"/api/rag/mock-interviews/{data['id']}").status_code == 204
    assert client.get(f"/api/rag/mock-interviews/{data['id']}").status_code == 404


def test_mock_interview_missing_key_returns_503(client):
    with _openai(_make_mock_ai(), key=""):
        resp = client.post("/api/rag/mock-interview", json={"job_text": JOB_TEXT})
    assert resp.status_code == 503


def test_mock_interview_openai_error_returns_502(client):
    with _openai(_make_mock_ai(chat_error=Exception("rate limit"))):
        resp = client.post("/api/rag/mock-interview", json={"job_text": JOB_TEXT})
    assert resp.status_code == 502
    assert client.get("/api/rag/mock-interviews").json() == []


def test_mock_interview_missing_id_returns_404(client):
    assert client.get("/api/rag/mock-interviews/999").status_code == 404
    assert client.delete("/api/rag/mock-interviews/999").status_code == 404


# ── resume-match ─────────────────────────────────────────────────────────────


def test_resume_match_uses_closest_docs_and_persists(client):
    _seed_rag_doc("experience", "最相關的經歷", [1.0, 0.0])
    _seed_rag_doc("project", "較不相關的專案", [0.0, 1.0])
    _seed_rag_doc("interview_question", "面試題不屬於履歷比對範圍", [1.0, 0.0])
    reply = {"gap_analysis": "缺 K8s", "answer_strategy": "強調 RAG", "match_score": 75}
    with _openai(_make_mock_ai(json.dumps(reply, ensure_ascii=False))):
        resp = client.post(
            "/api/rag/resume-match",
            json={"job_text": JOB_TEXT, "user_cv": "我的履歷", "job_url": "https://example.com/j"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["used_contexts"] == ["最相關的經歷", "較不相關的專案"]
    assert data["match_score"] == 75

    [listed] = client.get("/api/rag/resume-matches").json()
    assert listed["id"] == data["id"]
    detail = client.get(f"/api/rag/resume-matches/{data['id']}").json()
    assert detail["gap_analysis"] == "缺 K8s"
    assert detail["job_url"] == "https://example.com/j"

    assert client.delete(f"/api/rag/resume-matches/{data['id']}").status_code == 204
    assert client.get(f"/api/rag/resume-matches/{data['id']}").status_code == 404


def test_resume_match_missing_key_returns_503(client):
    with _openai(_make_mock_ai(), key=""):
        resp = client.post("/api/rag/resume-match", json={"job_text": JOB_TEXT, "user_cv": "履歷"})
    assert resp.status_code == 503


def test_resume_match_openai_error_returns_502(client):
    with _openai(_make_mock_ai(chat_error=Exception("rate limit"))):
        resp = client.post("/api/rag/resume-match", json={"job_text": JOB_TEXT, "user_cv": "履歷"})
    assert resp.status_code == 502
    assert client.get("/api/rag/resume-matches").json() == []


def test_resume_match_missing_id_returns_404(client):
    assert client.get("/api/rag/resume-matches/999").status_code == 404
    assert client.delete("/api/rag/resume-matches/999").status_code == 404
