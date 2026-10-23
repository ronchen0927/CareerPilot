"""Tests for /api/applications (kanban on the SQLite `jobs` table) and jobs-backed liveness."""

import asyncio
import sqlite3

import pytest

from app import db

JOB = {
    "url": "https://www.104.com.tw/job/abc",
    "job": "Backend Engineer",
    "company": "ACME",
    "city": "台北市",
    "salary": "月薪 60,000",
    "date": "2026/10/01",
}


@pytest.fixture
def app_client(client):
    return client


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
        conn.execute("UPDATE jobs SET status_changed_at = '2000-01-01 00:00:00'")

    body = {"url": JOB["url"], "status": "已投"}
    assert app_client.patch("/api/applications/status", json=body).status_code == 204
    row = _list(app_client)[0]
    assert row["status"] == "已投"
    assert row["status_changed_at"] != "2000-01-01 00:00:00"

    # Same status again: timestamp must not move.
    with sqlite3.connect(db_file) as conn:
        conn.execute("UPDATE jobs SET status_changed_at = '2000-01-01 00:00:00'")
    app_client.patch("/api/applications/status", json=body)
    assert _list(app_client)[0]["status_changed_at"] == "2000-01-01 00:00:00"


def test_set_status_invalid_and_missing(app_client):
    app_client.post("/api/applications", json=JOB)
    bad = app_client.patch("/api/applications/status", json={"url": JOB["url"], "status": "xx"})
    assert bad.status_code == 422
    missing = app_client.patch("/api/applications/status", json={"url": "nope", "status": "已投"})
    assert missing.status_code == 404


def test_remove_keeps_row_and_readd_restores(app_client, db_file):
    app_client.post("/api/applications", json={**JOB, "status": "面試中"})
    assert app_client.delete("/api/applications", params={"url": JOB["url"]}).status_code == 204
    assert _list(app_client) == []
    with sqlite3.connect(db_file) as conn:
        assert conn.execute("SELECT status FROM jobs WHERE url = ?", (JOB["url"],)).fetchall() == [
            (None,)
        ]
    assert app_client.delete("/api/applications", params={"url": JOB["url"]}).status_code == 404
    # Status updates don't apply to off-board rows.
    body = {"url": JOB["url"], "status": "已投"}
    assert app_client.patch("/api/applications/status", json=body).status_code == 404

    assert app_client.post("/api/applications", json=JOB).status_code == 204
    rows = _list(app_client)
    assert len(rows) == 1
    assert rows[0]["status"] == "想投"


def test_add_restores_liveness_only_row(app_client):
    asyncio.run(db.upsert_liveness(JOB["url"], "alive", None, 0))
    assert _list(app_client) == []
    app_client.post("/api/applications", json=JOB)
    rows = _list(app_client)
    assert len(rows) == 1
    assert rows[0]["job"] == JOB["job"]
    assert rows[0]["company"] == JOB["company"]


def test_import_duplicates_ignored(app_client):
    app_client.post("/api/applications", json={**JOB, "status": "面試中"})
    other = {**JOB, "url": "https://example.com/2", "status": "已投"}
    resp = app_client.post("/api/applications/import", json=[JOB, other, other])
    assert resp.status_code == 204
    rows = {r["url"]: r for r in _list(app_client)}
    assert len(rows) == 2
    assert rows[JOB["url"]]["status"] == "面試中"  # existing row untouched
    assert rows[other["url"]]["status"] == "已投"


def test_upsert_liveness_writes_jobs(app_client, db_file):
    app_client.post("/api/applications", json=JOB)
    asyncio.run(db.upsert_liveness(JOB["url"], "dead", "closed", 2))
    asyncio.run(db.upsert_liveness("https://example.com/new", "alive", None, 0))

    with sqlite3.connect(db_file) as conn:
        rows = dict(conn.execute("SELECT url, status FROM jobs").fetchall())
    assert rows == {JOB["url"]: "想投", "https://example.com/new": None}  # kanban untouched
    assert asyncio.run(db.get_liveness_fail_count(JOB["url"])) == 2

    m = asyncio.run(db.get_liveness_map([JOB["url"], "https://example.com/unchecked"]))
    assert set(m) == {JOB["url"]}
    assert m[JOB["url"]]["status"] == "dead"
    assert m[JOB["url"]]["last_reason"] == "closed"
    assert m[JOB["url"]]["last_checked"]

    status = app_client.post("/api/liveness/status", json={"urls": [JOB["url"]]}).json()
    assert status[JOB["url"]]["status"] == "dead"


def test_connect_enables_foreign_keys(db_file):
    async def check():
        async with db._connect() as conn:
            async with conn.execute("PRAGMA foreign_keys") as cur:
                return (await cur.fetchone())[0]

    assert asyncio.run(check()) == 1
