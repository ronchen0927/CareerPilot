"""Tests for /api/applications (kanban persisted in SQLite)."""

import sqlite3

import pytest

JOB = {
    "url": "https://www.104.com.tw/job/abc",
    "job": "Backend Engineer",
    "company": "ACME",
    "city": "台北市",
    "salary": "月薪 60,000",
    "date": "2026/10/01",
}


@pytest.fixture
def db_file(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    monkeypatch.setattr("app.config.settings.DB_PATH", str(path))
    monkeypatch.setattr("app.db._DB_PATH", path)
    return path


@pytest.fixture
def app_client(db_file, request):
    # Resolve `client` after the DB is redirected so lifespan's init_db() hits tmp_path.
    return request.getfixturevalue("client")


def _list(c):
    resp = c.get("/api/applications")
    assert resp.status_code == 200
    return resp.json()


def test_add_and_list(app_client):
    assert app_client.post("/api/applications", json=JOB).status_code == 204
    rows = _list(app_client)
    assert len(rows) == 1
    assert rows[0]["url"] == JOB["url"]
    assert rows[0]["status"] == "想投"
    assert rows[0]["evaluation_id"] is None


def test_set_status_updates_timestamp(app_client, db_file):
    app_client.post("/api/applications", json=JOB)
    # Backdate so the change is observable without sleeping.
    with sqlite3.connect(db_file) as conn:
        conn.execute("UPDATE applications SET status_changed_at = '2000-01-01 00:00:00'")

    body = {"url": JOB["url"], "status": "已投"}
    assert app_client.patch("/api/applications/status", json=body).status_code == 204
    row = _list(app_client)[0]
    assert row["status"] == "已投"
    assert row["status_changed_at"] != "2000-01-01 00:00:00"

    # Same status again: timestamp must not move.
    with sqlite3.connect(db_file) as conn:
        conn.execute("UPDATE applications SET status_changed_at = '2000-01-01 00:00:00'")
    app_client.patch("/api/applications/status", json=body)
    assert _list(app_client)[0]["status_changed_at"] == "2000-01-01 00:00:00"


def test_set_status_invalid_and_missing(app_client):
    app_client.post("/api/applications", json=JOB)
    bad = app_client.patch("/api/applications/status", json={"url": JOB["url"], "status": "xx"})
    assert bad.status_code == 422
    missing = app_client.patch("/api/applications/status", json={"url": "nope", "status": "已投"})
    assert missing.status_code == 404


def test_delete(app_client):
    app_client.post("/api/applications", json=JOB)
    assert app_client.delete("/api/applications", params={"url": JOB["url"]}).status_code == 204
    assert _list(app_client) == []
    assert app_client.delete("/api/applications", params={"url": JOB["url"]}).status_code == 404


def test_import_duplicates_ignored(app_client):
    app_client.post("/api/applications", json={**JOB, "status": "面試中"})
    other = {**JOB, "url": "https://example.com/2", "status": "已投"}
    resp = app_client.post("/api/applications/import", json=[JOB, other, other])
    assert resp.status_code == 204
    rows = {r["url"]: r for r in _list(app_client)}
    assert len(rows) == 2
    assert rows[JOB["url"]]["status"] == "面試中"  # existing row untouched
    assert rows[other["url"]]["status"] == "已投"
