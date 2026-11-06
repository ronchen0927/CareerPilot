from unittest.mock import patch

from app.config import settings

MISSING_KEY_DETAIL = "尚未設定 OPENAI_API_KEY，請在 backend/.env 加入 OPENAI_API_KEY=sk-..."


def test_rag_missing_key_returns_same_503_message_as_other_ai_endpoints(client):
    with patch.object(settings, "OPENAI_API_KEY", ""):
        rag = client.post(
            "/api/rag/documents", json={"doc_type": "project", "content": "做過一個 RAG 專案"}
        )
        cv = client.post("/api/cv/suggest-keywords", json={"cv_text": "x" * 100})
    assert rag.status_code == cv.status_code == 503
    assert rag.json()["detail"] == cv.json()["detail"] == MISSING_KEY_DETAIL
