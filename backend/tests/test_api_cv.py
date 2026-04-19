"""Tests for POST /api/cv/suggest-keywords."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestSuggestKeywords:
    def test_returns_keywords_list(self, client):
        with (
            patch("app.routers.cv.settings") as mock_settings,
            patch("app.routers.cv.AsyncOpenAI") as MockAI,
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            inst = MagicMock()
            MockAI.return_value = inst
            mock_resp = MagicMock()
            mock_resp.choices[
                0
            ].message.content = '{"keywords": ["後端工程師", "Python 工程師", "Django 開發"]}'
            inst.chat.completions.create = AsyncMock(return_value=mock_resp)

            resp = client.post(
                "/api/cv/suggest-keywords",
                json={"cv_text": "熟悉 Python、Django、PostgreSQL，有 3 年後端開發經驗"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "keywords" in data
        assert isinstance(data["keywords"], list)
        assert len(data["keywords"]) >= 1

    def test_missing_openai_key_returns_503(self, client):
        with patch("app.routers.cv.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            resp = client.post(
                "/api/cv/suggest-keywords",
                json={"cv_text": "熟悉 Python、Django，有 3 年後端開發經驗"},
            )
        assert resp.status_code == 503

    def test_cv_text_too_short_returns_422(self, client):
        resp = client.post(
            "/api/cv/suggest-keywords",
            json={"cv_text": "短"},
        )
        assert resp.status_code == 422

    def test_missing_cv_text_returns_422(self, client):
        resp = client.post("/api/cv/suggest-keywords", json={})
        assert resp.status_code == 422

    def test_openai_error_returns_502(self, client):
        with (
            patch("app.routers.cv.settings") as mock_settings,
            patch("app.routers.cv.AsyncOpenAI") as MockAI,
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            inst = MagicMock()
            MockAI.return_value = inst
            inst.chat.completions.create = AsyncMock(side_effect=Exception("rate limit"))

            resp = client.post(
                "/api/cv/suggest-keywords",
                json={"cv_text": "熟悉 Python、Django，有 3 年後端開發經驗"},
            )
        assert resp.status_code == 502
