"""Unit tests for scheduler.py pure helpers and notification dispatch."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.models import JobListing
from app.scheduler import DISCORD_MESSAGE_LIMIT, _is_due, _notify_discord, _send_notification


class TestIsDue:
    def _now(self):
        return datetime.now(UTC)

    def test_no_last_run_is_always_due(self):
        alert = {"interval_minutes": 60}
        assert _is_due(alert, self._now()) is True

    def test_just_ran_is_not_due(self):
        now = self._now()
        alert = {
            "last_run": now.isoformat(),
            "interval_minutes": 60,
        }
        assert _is_due(alert, now) is False

    def test_elapsed_past_interval_is_due(self):
        now = self._now()
        last = now - timedelta(minutes=61)
        alert = {
            "last_run": last.isoformat(),
            "interval_minutes": 60,
        }
        assert _is_due(alert, now) is True

    def test_exactly_at_interval_boundary_is_due(self):
        now = self._now()
        last = now - timedelta(minutes=60)
        alert = {
            "last_run": last.isoformat(),
            "interval_minutes": 60,
        }
        assert _is_due(alert, now) is True

    def test_just_under_interval_is_not_due(self):
        now = self._now()
        last = now - timedelta(minutes=59)
        alert = {
            "last_run": last.isoformat(),
            "interval_minutes": 60,
        }
        assert _is_due(alert, now) is False

    def test_invalid_last_run_treated_as_due(self):
        alert = {
            "last_run": "not-a-datetime",
            "interval_minutes": 60,
        }
        assert _is_due(alert, self._now()) is True

    @pytest.mark.parametrize("interval", [30, 60, 120, 1440])
    def test_various_intervals(self, interval):
        now = self._now()
        # Run exactly `interval` minutes ago → should be due
        last = now - timedelta(minutes=interval)
        alert = {"last_run": last.isoformat(), "interval_minutes": interval}
        assert _is_due(alert, now) is True

    def test_default_interval_used_when_missing(self):
        now = self._now()
        # 59 minutes ago, no interval_minutes key → defaults to 60 → not due
        last = now - timedelta(minutes=59)
        alert = {"last_run": last.isoformat()}
        assert _is_due(alert, now) is False


def _make_job(**overrides) -> JobListing:
    defaults = {
        "job": "Backend Engineer",
        "date": "2026-06-10",
        "link": "https://example.com/job/1",
        "company": "Acme",
        "city": "台北市",
        "experience": "3年以上",
        "education": "大學",
        "salary": "月薪 60,000 元",
    }
    return JobListing(**{**defaults, **overrides})


class TestSendNotification:
    def test_discord_type_dispatches_to_discord(self):
        alert = {
            "keyword": "Python",
            "notify_type": "discord",
            "notify_target": "https://discord.com/api/webhooks/123/abc",
        }
        with patch("app.scheduler._notify_discord", new=AsyncMock()) as mock_discord:
            asyncio.run(_send_notification(alert, [_make_job()]))
        mock_discord.assert_awaited_once()
        url, message = mock_discord.await_args.args
        assert url == alert["notify_target"]
        assert "Python" in message
        assert "Backend Engineer" in message

    def test_webhook_type_still_dispatches_to_webhook(self):
        alert = {
            "keyword": "Python",
            "notify_type": "webhook",
            "notify_target": "https://hooks.example.com/x",
        }
        with patch("app.scheduler._notify_webhook", new=AsyncMock()) as mock_webhook:
            asyncio.run(_send_notification(alert, [_make_job()]))
        mock_webhook.assert_awaited_once()

    def test_legacy_line_type_is_skipped_without_error(self):
        alert = {
            "keyword": "Python",
            "notify_type": "line",
            "notify_target": "legacy-token",
        }
        with (
            patch("app.scheduler._notify_discord", new=AsyncMock()) as mock_discord,
            patch("app.scheduler._notify_webhook", new=AsyncMock()) as mock_webhook,
        ):
            asyncio.run(_send_notification(alert, [_make_job()]))
        mock_discord.assert_not_awaited()
        mock_webhook.assert_not_awaited()


class TestNotifyDiscord:
    def _mock_session(self, status: int = 204):
        mock_resp = AsyncMock()
        mock_resp.status = status
        session = AsyncMock()
        session.post = AsyncMock(return_value=mock_resp)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        return session

    def test_posts_content_payload_to_webhook_url(self):
        session = self._mock_session()
        with patch("app.scheduler.aiohttp.ClientSession", return_value=session):
            asyncio.run(_notify_discord("https://discord.com/api/webhooks/123/abc", "hello"))
        session.post.assert_awaited_once_with(
            "https://discord.com/api/webhooks/123/abc", json={"content": "hello"}
        )

    def test_truncates_message_over_discord_limit(self):
        session = self._mock_session()
        long_message = "x" * (DISCORD_MESSAGE_LIMIT + 500)
        with patch("app.scheduler.aiohttp.ClientSession", return_value=session):
            asyncio.run(_notify_discord("https://discord.com/api/webhooks/123/abc", long_message))
        sent = session.post.await_args.kwargs["json"]["content"]
        assert len(sent) == DISCORD_MESSAGE_LIMIT
        assert sent.endswith("…")
