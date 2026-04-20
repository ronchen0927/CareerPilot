"""Tests for POST /api/jobs/evaluate with job_description field."""

from unittest.mock import AsyncMock, patch

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
