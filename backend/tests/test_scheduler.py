"""Unit tests for scheduler.py pure helpers."""

from datetime import UTC, datetime, timedelta

import pytest

from app.scheduler import _is_due


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
