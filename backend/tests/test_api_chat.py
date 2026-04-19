"""Tests for POST /api/chat streaming endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import openai


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


def _make_fake_stream(contents: list[str]):
    """Return an async generator that yields mock OpenAI chunks."""

    async def _gen():
        for text in contents:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = text
            yield chunk

    return _gen()


class TestChat:
    def test_streams_text_response(self, client):
        with (
            patch("app.routers.chat.settings") as mock_settings,
            patch("app.routers.chat.AsyncOpenAI") as MockAI,
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            inst = MagicMock()
            MockAI.return_value = inst
            inst.chat.completions.create = AsyncMock(return_value=_make_fake_stream(["你好", "！"]))
            resp = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": "我適合嗎？"}],
                    "job": _job_payload(),
                    "user_cv": "Python 工程師，3 年經驗",
                },
            )
        assert resp.status_code == 200
        assert "你好" in resp.text
        assert "！" in resp.text

    def test_empty_messages_still_returns_200(self, client):
        with (
            patch("app.routers.chat.settings") as mock_settings,
            patch("app.routers.chat.AsyncOpenAI") as MockAI,
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            inst = MagicMock()
            MockAI.return_value = inst
            inst.chat.completions.create = AsyncMock(return_value=_make_fake_stream(["開始吧"]))
            resp = client.post(
                "/api/chat",
                json={"messages": [], "job": _job_payload(), "user_cv": ""},
            )
        assert resp.status_code == 200

    def test_missing_openai_key_returns_503(self, client):
        with patch("app.routers.chat.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            resp = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": "test"}],
                    "job": _job_payload(),
                    "user_cv": "",
                },
            )
        assert resp.status_code == 503

    def test_missing_messages_field_returns_422(self, client):
        resp = client.post(
            "/api/chat",
            json={"job": _job_payload(), "user_cv": ""},
        )
        assert resp.status_code == 422

    def test_missing_job_field_returns_422(self, client):
        resp = client.post(
            "/api/chat",
            json={"messages": [], "user_cv": ""},
        )
        assert resp.status_code == 422

    def test_openai_error_yields_warning_marker(self, client):
        with (
            patch("app.routers.chat.settings") as mock_settings,
            patch("app.routers.chat.AsyncOpenAI") as MockAI,
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            inst = MagicMock()
            MockAI.return_value = inst
            inst.chat.completions.create = AsyncMock(side_effect=openai.OpenAIError("rate limit"))
            resp = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": "我適合嗎？"}],
                    "job": _job_payload(),
                    "user_cv": "Python 工程師，3 年經驗",
                },
            )
        assert resp.status_code == 200
        assert "⚠" in resp.text
