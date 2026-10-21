"""#86 phase 2: records link to the `jobs` table via job_id."""

import asyncio
import json
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import db
from app.models import JobEvaluateResponse

URL = "https://www.104.com.tw/job/abc"
JD = "後端工程師，需要熟悉 Python 與 FastAPI，台北市"
CV = "3 年 Python 經驗"


def _ai(content: str) -> MagicMock:
    inst = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.content = content
    inst.chat.completions.create = AsyncMock(return_value=resp)
    return inst


def _evaluate_text(client, **extra):
    fake = JobEvaluateResponse(score="A", summary="s", recommendation="r")
    with (
        patch("app.routers.evaluate.settings") as s,
        patch("app.routers.evaluate._call_openai", AsyncMock(return_value=fake)),
    ):
        s.OPENAI_API_KEY = "sk-test"
        return client.post("/api/jobs/evaluate-text", json={"job_text": JD, "user_cv": CV, **extra})


def _evaluate_structured(client, **extra):
    fake = JobEvaluateResponse(score="B", summary="s", recommendation="r")
    job = {
        "job": "Backend",
        "date": "2026/10/01",
        "link": URL,
        "company": "ACME",
        "city": "台北市",
        "experience": "1-3年",
        "education": "大學",
        "salary": "面議",
    }
    with (
        patch("app.routers.evaluate.settings") as s,
        patch("app.routers.evaluate._call_openai", AsyncMock(return_value=fake)),
    ):
        s.OPENAI_API_KEY = "sk-test"
        return client.post("/api/jobs/evaluate", json={"job": job, **extra})


def _cover_letter(client, **extra):
    with (
        patch("app.routers.cover_letter.settings") as s,
        patch("app.routers.cover_letter.AsyncOpenAI", return_value=_ai("信件內容")),
    ):
        s.OPENAI_API_KEY = "sk-test"
        return client.post("/api/jobs/cover-letter", json={"job_text": JD, **extra})


def _resume_rewrite(client, **extra):
    with (
        patch("app.routers.resume.settings") as s,
        patch("app.routers.resume.AsyncOpenAI", return_value=_ai("改寫後履歷")),
    ):
        s.OPENAI_API_KEY = "sk-test"
        return client.post(
            "/api/jobs/resume-rewrite", json={"job_text": JD, "user_cv": CV, **extra}
        )


def _rag(client, path, content, **extra):
    with (
        patch("app.routers.rag.settings") as s,
        patch("app.routers.rag.AsyncOpenAI", return_value=_ai(json.dumps(content))),
        patch("app.routers.rag._get_embedding", AsyncMock(return_value=[1.0])),
    ):
        s.OPENAI_API_KEY = "sk-test"
        return client.post(path, json={"job_text": JD, **extra})


def _mock_interview(client, **extra):
    data = {"technical_questions": ["q"], "behavioral_questions": ["b"], "tips": "t"}
    return _rag(client, "/api/rag/mock-interview", data, **extra)


def _resume_match(client, **extra):
    data = {"gap_analysis": "g", "answer_strategy": "a", "match_score": 80}
    return _rag(client, "/api/rag/resume-match", data, user_cv=CV, **extra)


GENERATORS = [_evaluate_text, _cover_letter, _resume_rewrite, _mock_interview, _resume_match]


def _job_ids(db_file, table):
    with sqlite3.connect(db_file) as conn:
        return [r[0] for r in conn.execute(f"SELECT job_id FROM {table}")]  # noqa: S608


@pytest.mark.parametrize("gen", GENERATORS)
def test_explicit_job_id_is_stored(client, gen):
    job_id = asyncio.run(db.get_or_create_job(None, "jd"))
    resp = gen(client, job_id=job_id)
    assert resp.status_code == 200, resp.text
    assert resp.json()["job_id"] == job_id


@pytest.mark.parametrize("gen", GENERATORS)
def test_same_url_resolves_to_kanban_job(client, gen):
    client.post("/api/applications", json={"url": URL, "job": "Backend", "status": "已投"})
    board_id = client.get("/api/applications").json()[0]["id"]
    resp = gen(client, job_url=URL)
    assert resp.status_code == 200, resp.text
    assert resp.json()["job_id"] == board_id
    # Kanban state untouched by the linking upsert.
    assert client.get("/api/applications").json()[0]["status"] == "已投"


def test_no_url_creates_new_job_each_time(client, db_file):
    a = _cover_letter(client).json()["job_id"]
    b = _cover_letter(client).json()["job_id"]
    assert a != b
    assert _job_ids(db_file, "cover_letters") == [a, b]


def test_unknown_job_id_falls_back_to_url(client):
    resp = _resume_rewrite(client, job_id=999, job_url=URL)
    assert resp.status_code == 200
    assert resp.json()["job_id"] != 999


def test_evaluate_then_board_share_job(client, db_file):
    eval_id = _evaluate_structured(client).json()["job_id"]
    client.post("/api/applications", json={"url": URL, "job": "Backend"})
    rows = client.get("/api/applications").json()
    assert [r["id"] for r in rows] == [eval_id]
    with sqlite3.connect(db_file) as conn:
        assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone() == (1,)


def test_cache_hit_backfills_job_id(client, db_file):
    first = _evaluate_text(client).json()
    with sqlite3.connect(db_file) as conn:
        conn.execute("UPDATE evaluations SET job_id = NULL")  # simulate a pre-#86 row
    resp = _evaluate_text(client, job_url=URL)
    assert resp.json()["from_cache"] is True
    job_id = resp.json()["job_id"]
    assert job_id is not None and job_id != first["job_id"]
    assert _job_ids(db_file, "evaluations") == [job_id]
    assert asyncio.run(db.list_liveness_targets()) == [URL]


def test_cache_hit_url_attaches_to_existing_job(client):
    job_id = _evaluate_text(client).json()["job_id"]
    assert asyncio.run(db.list_liveness_targets()) == []
    resp = _evaluate_text(client, job_url=URL)
    assert resp.json()["job_id"] == job_id
    assert asyncio.run(db.list_liveness_targets()) == [URL]


def test_liveness_targets_only_from_jobs(client):
    _evaluate_text(client, job_url=URL)
    client.post("/api/applications", json={"url": "https://example.com/2", "job": "x"})
    _cover_letter(client)  # url-less job: not a target
    assert sorted(asyncio.run(db.list_liveness_targets())) == sorted([URL, "https://example.com/2"])


def test_backfill_migration_is_idempotent(client, db_file):
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "INSERT INTO evaluations (job_hash, job_text, job_url, score, summary,"
            " match_points, gap_points, recommendation) VALUES ('h', 'jd', ?, 'A', 's',"
            " '[]', '[]', 'r')",
            (URL,),
        )
        conn.execute(
            "INSERT INTO resume_rewrites (job_text, job_url, original_cv, mode, result)"
            " VALUES ('jd', ?, 'cv', 'plain', 'r')",
            (URL,),
        )
    asyncio.run(db.init_db())
    asyncio.run(db.init_db())
    with sqlite3.connect(db_file) as conn:
        jobs = conn.execute("SELECT id, url FROM jobs").fetchall()
    assert len(jobs) == 1 and jobs[0][1] == URL
    assert _job_ids(db_file, "evaluations") == [jobs[0][0]]
    assert _job_ids(db_file, "resume_rewrites") == [jobs[0][0]]
    assert asyncio.run(db.list_liveness_targets()) == [URL]


def test_records_endpoint(client):
    ids = {g.__name__: g(client, job_url=URL).json() for g in GENERATORS}
    job_id = ids["_evaluate_text"]["job_id"]
    _cover_letter(client)  # other job, must not show up
    records = client.get(f"/api/applications/{job_id}/records").json()
    assert records == {
        "evaluations": [1],
        "cover_letters": [ids["_cover_letter"]["id"]],
        "resume_rewrites": [ids["_resume_rewrite"]["id"]],
        "resume_matches": [ids["_resume_match"]["id"]],
        "mock_interviews": [ids["_mock_interview"]["id"]],
    }
    empty = client.get("/api/applications/999/records").json()
    assert all(v == [] for v in empty.values())


def test_deleting_job_nulls_children(client, db_file):
    job_id = _cover_letter(client, job_url=URL).json()["job_id"]

    async def delete():
        async with db._connect() as conn:
            await conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            await conn.commit()

    asyncio.run(delete())
    assert _job_ids(db_file, "cover_letters") == [None]
