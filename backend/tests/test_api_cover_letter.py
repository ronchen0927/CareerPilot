"""Tests for cover letter endpoints — greeting/closing fields and extract-company."""

from unittest.mock import AsyncMock, MagicMock, patch


def _make_mock_ai(content: str):
    """回傳 mock AI instance，content 為 AI 回傳文字。"""
    inst = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = content
    inst.chat.completions.create = AsyncMock(return_value=mock_resp)
    return inst


class TestGenerateCoverLetterGreetingClosing:
    def test_returns_letter_with_company_and_name(self, client):
        inst = _make_mock_ai("親愛的 ACME 招募夥伴：\n\n正文內容...\n\n此致 敬禮\nPin Yuan Chen")
        with (
            patch("app.routers.cover_letter.settings") as mock_settings,
            patch("app.routers.cover_letter.AsyncOpenAI", return_value=inst),
            patch("app.routers.cover_letter.save_cover_letter", new=AsyncMock(return_value=1)),
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            resp = client.post(
                "/api/jobs/cover-letter",
                json={
                    "job_text": "後端工程師，熟悉 Python，ACME 公司",
                    "user_cv": "3 年 Python 經驗",
                    "company_name": "ACME",
                    "user_name": "Pin Yuan Chen",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "letter" in data
        assert "id" in data

    def test_returns_letter_without_optional_fields(self, client):
        inst = _make_mock_ai("正文內容...")
        with (
            patch("app.routers.cover_letter.settings") as mock_settings,
            patch("app.routers.cover_letter.AsyncOpenAI", return_value=inst),
            patch("app.routers.cover_letter.save_cover_letter", new=AsyncMock(return_value=2)),
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            resp = client.post(
                "/api/jobs/cover-letter",
                json={"job_text": "後端工程師，熟悉 Python", "user_cv": ""},
            )
        assert resp.status_code == 200

    def test_missing_openai_key_returns_503(self, client):
        with patch("app.routers.cover_letter.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            resp = client.post(
                "/api/jobs/cover-letter",
                json={"job_text": "後端工程師職缺描述，需熟悉 Python", "user_cv": ""},
            )
        assert resp.status_code == 503


class TestExtractCompanyName:
    def test_returns_company_name(self, client):
        inst = _make_mock_ai("ACME 科技")
        with (
            patch("app.routers.cover_letter.settings") as mock_settings,
            patch("app.routers.cover_letter.AsyncOpenAI", return_value=inst),
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            resp = client.post(
                "/api/jobs/extract-company",
                json={"job_text": "ACME 科技招募後端工程師，需熟悉 Python"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "company_name" in data
        assert data["company_name"] == "ACME 科技"

    def test_returns_empty_string_when_not_found(self, client):
        inst = _make_mock_ai("")
        with (
            patch("app.routers.cover_letter.settings") as mock_settings,
            patch("app.routers.cover_letter.AsyncOpenAI", return_value=inst),
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            resp = client.post(
                "/api/jobs/extract-company",
                json={"job_text": "招募後端工程師，需熟悉 Python"},
            )
        assert resp.status_code == 200
        assert resp.json()["company_name"] == ""

    def test_missing_openai_key_returns_503(self, client):
        with patch("app.routers.cover_letter.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            resp = client.post(
                "/api/jobs/extract-company",
                json={"job_text": "後端工程師職缺描述，需熟悉 Python"},
            )
        assert resp.status_code == 503

    def test_job_text_too_short_returns_422(self, client):
        resp = client.post("/api/jobs/extract-company", json={"job_text": "短"})
        assert resp.status_code == 422

    def test_openai_error_returns_502(self, client):
        inst = MagicMock()
        inst.chat.completions.create = AsyncMock(side_effect=Exception("rate limit"))
        with (
            patch("app.routers.cover_letter.settings") as mock_settings,
            patch("app.routers.cover_letter.AsyncOpenAI", return_value=inst),
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            resp = client.post(
                "/api/jobs/extract-company",
                json={"job_text": "ACME 科技招募後端工程師職缺"},
            )
        assert resp.status_code == 502
