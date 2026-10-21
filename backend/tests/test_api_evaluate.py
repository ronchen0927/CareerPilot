"""Tests for POST /api/jobs/evaluate with job_description field."""

import asyncio
from unittest.mock import AsyncMock, patch

from app.db import list_liveness_targets
from app.models import JobEvaluateResponse


def _job_payload(**kwargs) -> dict:
    base = {
        "job": "後端工程師",
        "date": "2026/01/01",
        "link": "https://www.104.com.tw/job/abc",
        "company": "測試公司",
        "city": "台北市",
        "experience": "1-3年",
        "education": "大學",
        "salary": "50,000 ~ 70,000 元",
        "salary_low": 50000,
        "salary_high": 70000,
        "is_featured": False,
        "source": "104",
    }
    base.update(kwargs)
    return base


_FAKE_RESULT = JobEvaluateResponse(
    score="A",
    summary="良好匹配",
    match_points=["技能符合"],
    gap_points=[],
    recommendation="建議投遞",
)


def test_job_description_included_in_prompt(client):
    captured = {}

    async def fake_call_openai(openai_client, prompt):
        captured["prompt"] = prompt
        return _FAKE_RESULT

    with (
        patch("app.routers.evaluate.settings") as mock_settings,
        patch("app.routers.evaluate._call_openai", fake_call_openai),
        patch("app.routers.evaluate.get_cached", AsyncMock(return_value=None)),
        patch("app.routers.evaluate.save_evaluation", AsyncMock()),
    ):
        mock_settings.OPENAI_API_KEY = "sk-test"
        resp = client.post(
            "/api/jobs/evaluate",
            json={
                "job": _job_payload(),
                "user_cv": "",
                "job_description": "需要熟悉 Python、FastAPI、PostgreSQL",
            },
        )
    assert resp.status_code == 200
    assert "FastAPI" in captured["prompt"]
    assert "PostgreSQL" in captured["prompt"]


def test_evaluate_without_job_description_omits_jd_section(client):
    captured = {}

    async def fake_call_openai(openai_client, prompt):
        captured["prompt"] = prompt
        return _FAKE_RESULT

    with (
        patch("app.routers.evaluate.settings") as mock_settings,
        patch("app.routers.evaluate._call_openai", fake_call_openai),
        patch("app.routers.evaluate.get_cached", AsyncMock(return_value=None)),
        patch("app.routers.evaluate.save_evaluation", AsyncMock()),
    ):
        mock_settings.OPENAI_API_KEY = "sk-test"
        resp = client.post(
            "/api/jobs/evaluate",
            json={"job": _job_payload(), "user_cv": ""},
        )
    assert resp.status_code == 200
    assert "Job Description" not in captured["prompt"]


# ── /api/jobs/evaluate-text job_url persistence (issue #60) ──────────────────

_JD = "後端工程師，需要熟悉 Python 與 FastAPI，台北市"
_URL = "https://www.104.com.tw/job/xyz"


def _post_evaluate_text(client, **extra):
    with (
        patch("app.routers.evaluate.settings") as mock_settings,
        patch("app.routers.evaluate._call_openai", AsyncMock(return_value=_FAKE_RESULT)),
    ):
        mock_settings.OPENAI_API_KEY = "sk-test"
        return client.post("/api/jobs/evaluate-text", json={"job_text": _JD, **extra})


def test_evaluate_text_saves_job_url(client):
    resp = _post_evaluate_text(client, job_url=_URL)
    assert resp.status_code == 200
    assert asyncio.run(list_liveness_targets()) == [_URL]


def test_evaluate_text_without_url_not_tracked(client):
    assert _post_evaluate_text(client).status_code == 200
    assert asyncio.run(list_liveness_targets()) == []


def test_evaluate_text_cache_hit_backfills_job_url(client):
    assert _post_evaluate_text(client).status_code == 200
    assert asyncio.run(list_liveness_targets()) == []

    resp = _post_evaluate_text(client, job_url=_URL)
    assert resp.status_code == 200
    assert resp.json()["score"] == "A"
    assert asyncio.run(list_liveness_targets()) == [_URL]
