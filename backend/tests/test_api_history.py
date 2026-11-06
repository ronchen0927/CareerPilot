"""Tests for /api/evaluations (history router) against a temp SQLite DB."""

import asyncio

from app import db

JOB_TEXT = "後端工程師，熟悉 Python 與 FastAPI，三年以上經驗，具備雲端部署能力與團隊合作精神"


def _seed_evaluation() -> int:
    return asyncio.run(
        db.save_evaluation(
            job_hash="h1",
            job_text=JOB_TEXT,
            job_url="https://example.com/job/1",
            score="B",
            summary="大致符合",
            match_points=["Python"],
            gap_points=["K8s"],
            recommendation="可投遞",
            dimensions={"skill_match": 80},
        )
    )


def test_list_returns_saved_evaluation(client):
    record_id = _seed_evaluation()
    resp = client.get("/api/evaluations")
    assert resp.status_code == 200
    [rec] = resp.json()
    assert rec["id"] == record_id
    assert rec["job_text_snippet"] and JOB_TEXT.startswith(rec["job_text_snippet"])
    assert rec["match_points"] == ["Python"]
    assert rec["gap_points"] == ["K8s"]


def test_list_empty(client):
    assert client.get("/api/evaluations").json() == []


def test_get_by_id(client):
    record_id = _seed_evaluation()
    resp = client.get(f"/api/evaluations/{record_id}")
    assert resp.status_code == 200
    rec = resp.json()
    assert rec["job_text"] == JOB_TEXT
    assert rec["job_url"] == "https://example.com/job/1"
    assert rec["score"] == "B"


def test_get_missing_returns_404(client):
    assert client.get("/api/evaluations/999").status_code == 404


def test_delete_then_gone(client):
    record_id = _seed_evaluation()
    assert client.delete(f"/api/evaluations/{record_id}").status_code == 204
    assert client.get(f"/api/evaluations/{record_id}").status_code == 404
    assert client.delete(f"/api/evaluations/{record_id}").status_code == 404
