"""Tests for /api/liveness/status and /api/liveness/check."""

import asyncio
from unittest.mock import AsyncMock, patch

from app import db

URL = "https://example.com/job/1"


def test_status_returns_only_checked_urls(client):
    asyncio.run(db.upsert_liveness(URL, "dead", "職缺已關閉", 2))
    resp = client.post(
        "/api/liveness/status", json={"urls": [URL, "https://example.com/unchecked"]}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert list(data) == [URL]
    assert data[URL]["status"] == "dead"
    assert data[URL]["reason"] == "職缺已關閉"
    assert data[URL]["last_checked"]


def test_status_empty_list(client):
    resp = client.post("/api/liveness/status", json={"urls": []})
    assert resp.status_code == 200
    assert resp.json() == {}


def test_check_triggers_check_urls(client):
    with patch("app.routers.liveness.check_urls", new=AsyncMock(return_value=1)) as mock_check:
        resp = client.post("/api/liveness/check", json={"urls": [URL]})
    assert resp.status_code == 200
    assert resp.json() == {"checked": 1}
    mock_check.assert_awaited_once_with([URL])


def test_status_missing_urls_returns_422(client):
    assert client.post("/api/liveness/status", json={}).status_code == 422


def test_check_missing_urls_returns_422(client):
    assert client.post("/api/liveness/check", json={}).status_code == 422
