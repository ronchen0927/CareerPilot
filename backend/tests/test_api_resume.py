"""Tests for resume-rewrite endpoints against a temp SQLite DB, OpenAI mocked."""

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

JOB_TEXT = "後端工程師，熟悉 Python 與 FastAPI"
PAYLOAD = {
    "job_text": JOB_TEXT,
    "user_cv": "3 年 Python 經驗",
    "job_url": "https://example.com/job/1",
}


def _make_mock_ai(content: str | None = None, error: Exception | None = None):
    inst = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.content = content
    inst.chat.completions.create = AsyncMock(return_value=resp, side_effect=error)
    return inst


@contextmanager
def _openai(inst, key: str = "sk-test"):
    with (
        patch("app.openai_client.settings") as mock_settings,
        patch("app.openai_client.AsyncOpenAI", return_value=inst),
    ):
        mock_settings.OPENAI_API_KEY = key
        yield


def test_rewrite_saves_and_is_listed(client):
    with _openai(_make_mock_ai("  改寫後的履歷  ")):
        resp = client.post("/api/jobs/resume-rewrite", json=PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "改寫後的履歷"
    assert isinstance(data["job_id"], int)

    [rec] = client.get("/api/resume-rewrites").json()
    assert rec["id"] == data["id"]
    assert rec["original_cv"] == "3 年 Python 經驗"

    detail = client.get(f"/api/resume-rewrites/{data['id']}").json()
    assert detail["result"] == "改寫後的履歷"
    assert detail["job_url"] == "https://example.com/job/1"


def test_missing_openai_key_returns_503(client):
    with _openai(_make_mock_ai("x"), key=""):
        resp = client.post("/api/jobs/resume-rewrite", json=PAYLOAD)
    assert resp.status_code == 503


def test_openai_error_returns_502(client):
    with _openai(_make_mock_ai(error=Exception("rate limit"))):
        resp = client.post("/api/jobs/resume-rewrite", json=PAYLOAD)
    assert resp.status_code == 502
    assert client.get("/api/resume-rewrites").json() == []


def test_empty_ai_reply_returns_502(client):
    with _openai(_make_mock_ai("   ")):
        resp = client.post("/api/jobs/resume-rewrite", json=PAYLOAD)
    assert resp.status_code == 502


def test_get_missing_returns_404(client):
    assert client.get("/api/resume-rewrites/999").status_code == 404


def test_delete_then_gone(client):
    with _openai(_make_mock_ai("改寫後的履歷")):
        record_id = client.post("/api/jobs/resume-rewrite", json=PAYLOAD).json()["id"]
    assert client.delete(f"/api/resume-rewrites/{record_id}").status_code == 204
    assert client.get(f"/api/resume-rewrites/{record_id}").status_code == 404
    assert client.delete(f"/api/resume-rewrites/{record_id}").status_code == 404
