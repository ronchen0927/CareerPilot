"""
Shared pytest fixtures.

- `tmp_alerts_file`: redirects ALERTS_FILE to a tmp path for isolation
- `client`: FastAPI TestClient with scheduler mocked out (no real background task)
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_alerts_file(tmp_path, monkeypatch):
    """Return a temp Path and patch ALERTS_FILE to point at it."""
    alerts_file = tmp_path / "alerts.json"
    monkeypatch.setattr("app.alerts.ALERTS_FILE", alerts_file)
    return alerts_file


@pytest.fixture
def client(tmp_alerts_file):
    """
    TestClient that:
    - uses a temp alerts.json (no real file left behind)
    - replaces run_scheduler and run_liveness_loop with no-ops
    - mocks all non-104 scrapers to return [] so no real network calls occur;
      individual tests override scrape_104 to supply specific fixture data
    """
    with (
        patch("app.scheduler.run_scheduler", new_callable=AsyncMock),
        patch("app.liveness.run_liveness_loop", new_callable=AsyncMock),
        patch("app.routers.jobs.scrape_cake", new=AsyncMock(return_value=[])),
        patch("app.routers.jobs.scrape_yourator", new=AsyncMock(return_value=[])),
        patch("app.routers.jobs.scrape_meetjob", new=AsyncMock(return_value=[])),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


@pytest.fixture
def sample_alert_payload():
    return {
        "keyword": "Python",
        "areas": ["6001001000"],
        "experience": ["3"],
        "pages": 2,
        "min_salary": 50000,
        "notify_type": "line",
        "notify_target": "test-token-abc",
        "interval_minutes": 60,
    }


@pytest.fixture
def created_alert(client, sample_alert_payload):
    """Create one alert and return the response JSON."""
    resp = client.post("/api/alerts", json=sample_alert_payload)
    assert resp.status_code == 201
    return resp.json()


def make_alerts_file(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
