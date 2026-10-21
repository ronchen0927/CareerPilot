import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from .config import settings

_DB_PATH: Path | None = None


def _db_path() -> Path:
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = Path(settings.DB_PATH)
    return _DB_PATH


@asynccontextmanager
async def _connect() -> AsyncIterator[aiosqlite.Connection]:
    """Open a connection with foreign-key enforcement (SQLite disables it per connection)."""
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        yield db


async def init_db() -> None:
    async with _connect() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                job_hash        TEXT    NOT NULL UNIQUE,
                job_text        TEXT    NOT NULL,
                job_url         TEXT,
                score           TEXT    NOT NULL,
                summary         TEXT    NOT NULL,
                match_points    TEXT    NOT NULL,
                gap_points      TEXT    NOT NULL,
                recommendation  TEXT    NOT NULL,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """
        )
        # Idempotent migration: add dimensions column for multi-dimensional scoring
        async with db.execute("PRAGMA table_info(evaluations)") as cur:
            cols = {row[1] for row in await cur.fetchall()}
        if "dimensions" not in cols:
            await db.execute("ALTER TABLE evaluations ADD COLUMN dimensions TEXT")

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS cover_letters (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                job_text   TEXT    NOT NULL,
                letter     TEXT    NOT NULL,
                created_at TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS resume_rewrites (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                job_text    TEXT    NOT NULL,
                job_url     TEXT,
                original_cv TEXT    NOT NULL,
                mode        TEXT    NOT NULL,
                result      TEXT    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS rag_documents (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_type    TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                embedding   TEXT    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS resume_matches (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                job_text       TEXT    NOT NULL,
                job_url        TEXT,
                user_cv        TEXT    NOT NULL,
                gap_analysis   TEXT    NOT NULL,
                answer_strategy TEXT    NOT NULL,
                match_score    INTEGER NOT NULL,
                created_at     TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS mock_interviews (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                job_text             TEXT    NOT NULL,
                technical_questions  TEXT    NOT NULL,
                behavioral_questions TEXT    NOT NULL,
                tips                 TEXT    NOT NULL,
                created_at           TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """
        )
        # applications (unmerged PR #83) became jobs; job_liveness is a recomputable
        # cache now folded into jobs (#86). Both only ever held throwaway data.
        await db.execute("DROP TABLE IF EXISTS applications")
        await db.execute("DROP TABLE IF EXISTS job_liveness")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                url               TEXT    UNIQUE,
                job               TEXT    NOT NULL DEFAULT '',
                company           TEXT    NOT NULL DEFAULT '',
                city              TEXT    NOT NULL DEFAULT '',
                salary            TEXT    NOT NULL DEFAULT '',
                date              TEXT    NOT NULL DEFAULT '',
                job_text          TEXT,
                status            TEXT,  -- NULL = not on the kanban
                status_changed_at TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                evaluation_id     INTEGER REFERENCES evaluations(id) ON DELETE SET NULL,
                reason            TEXT,
                notes             TEXT,
                liveness_status   TEXT    NOT NULL DEFAULT 'unknown',
                liveness_reason   TEXT,
                fail_count        INTEGER NOT NULL DEFAULT 0,
                last_checked      TEXT,
                created_at        TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """
        )
        await db.commit()


async def get_evaluation(record_id: int) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM evaluations WHERE id = ?", (record_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def get_cached(job_hash: str) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM evaluations WHERE job_hash = ?", (job_hash,)) as cur:
            row = await cur.fetchone()
    if row is None:
        return None
    return dict(row)


async def save_evaluation(
    job_hash: str,
    job_text: str,
    job_url: str | None,
    score: str,
    summary: str,
    match_points: list[str],
    gap_points: list[str],
    recommendation: str,
    dimensions: dict | None = None,
) -> int:
    async with _connect() as db:
        cur = await db.execute(
            """
            INSERT INTO evaluations
                (job_hash, job_text, job_url, score, summary,
                 match_points, gap_points, recommendation, dimensions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_hash,
                job_text,
                job_url,
                score,
                summary,
                json.dumps(match_points, ensure_ascii=False),
                json.dumps(gap_points, ensure_ascii=False),
                recommendation,
                json.dumps(dimensions, ensure_ascii=False) if dimensions else None,
            ),
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


async def set_evaluation_url(record_id: int, job_url: str) -> None:
    """Backfill job_url on an evaluation that was saved without one."""
    async with _connect() as db:
        await db.execute(
            "UPDATE evaluations SET job_url = ? WHERE id = ? AND job_url IS NULL",
            (job_url, record_id),
        )
        await db.commit()


async def list_evaluations() -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM evaluations ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def delete_evaluation(record_id: int) -> bool:
    async with _connect() as db:
        cur = await db.execute("DELETE FROM evaluations WHERE id = ?", (record_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Cover letters ─────────────────────────────────────────────────────────────


async def save_cover_letter(job_text: str, letter: str) -> int:
    async with _connect() as db:
        cur = await db.execute(
            "INSERT INTO cover_letters (job_text, letter) VALUES (?, ?)",
            (job_text, letter),
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


async def list_cover_letters() -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM cover_letters ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_cover_letter(record_id: int) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM cover_letters WHERE id = ?", (record_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def delete_cover_letter(record_id: int) -> bool:
    async with _connect() as db:
        cur = await db.execute("DELETE FROM cover_letters WHERE id = ?", (record_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Resume rewrites ───────────────────────────────────────────────────────────


async def save_resume_rewrite(
    job_text: str,
    job_url: str | None,
    original_cv: str,
    result: str,
) -> int:
    async with _connect() as db:
        cur = await db.execute(
            """
            INSERT INTO resume_rewrites
                (job_text, job_url, original_cv, mode, result)
            VALUES (?, ?, ?, 'plain', ?)
            """,
            (job_text, job_url, original_cv, result),
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


async def list_resume_rewrites() -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM resume_rewrites ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_resume_rewrite(record_id: int) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM resume_rewrites WHERE id = ?", (record_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def delete_resume_rewrite(record_id: int) -> bool:
    async with _connect() as db:
        cur = await db.execute("DELETE FROM resume_rewrites WHERE id = ?", (record_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Job liveness ──────────────────────────────────────────────────────────────


async def upsert_liveness(job_url: str, status: str, reason: str | None, fail_count: int) -> None:
    """Write liveness fields only; creates an off-kanban jobs row if the url is new."""
    async with _connect() as db:
        await db.execute(
            """
            INSERT INTO jobs (url, liveness_status, liveness_reason, fail_count, last_checked)
            VALUES (?, ?, ?, ?, datetime('now','localtime'))
            ON CONFLICT(url) DO UPDATE SET
                liveness_status = excluded.liveness_status,
                liveness_reason = excluded.liveness_reason,
                fail_count      = excluded.fail_count,
                last_checked    = excluded.last_checked
            """,
            (job_url, status, reason, fail_count),
        )
        await db.commit()


async def get_liveness_map(urls: list[str]) -> dict[str, dict]:
    """Checked urls only, keyed by url, in the old job_liveness row shape."""
    if not urls:
        return {}
    placeholders = ",".join("?" * len(urls))
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT url AS job_url, liveness_status AS status, last_checked,"  # noqa: S608
            " liveness_reason AS last_reason, fail_count FROM jobs"
            f" WHERE last_checked IS NOT NULL AND url IN ({placeholders})",
            urls,
        ) as cur:
            rows = await cur.fetchall()
    return {r["job_url"]: dict(r) for r in rows}


async def get_liveness_fail_count(job_url: str) -> int:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT fail_count FROM jobs WHERE url = ?", (job_url,)) as cur:
            row = await cur.fetchone()
    return row["fail_count"] if row else 0


async def list_liveness_targets() -> list[str]:
    """Distinct urls from jobs plus evaluations.job_url.

    Transitional (#86 phase 1): evaluations don't write to jobs yet, so their urls
    are unioned in. Drop the evaluations half once phase 2 links them via job_id.
    """
    async with _connect() as db:
        async with db.execute(
            "SELECT url FROM jobs WHERE url IS NOT NULL"
            " UNION SELECT job_url FROM evaluations WHERE job_url IS NOT NULL"
        ) as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


# ── RAG Documents ─────────────────────────────────────────────────────────────


async def save_rag_document(doc_type: str, content: str, embedding: list[float]) -> int:
    async with _connect() as db:
        cur = await db.execute(
            "INSERT INTO rag_documents (doc_type, content, embedding) VALUES (?, ?, ?)",
            (doc_type, content, json.dumps(embedding)),
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


async def list_rag_documents(doc_type: str | None = None) -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        if doc_type:
            async with db.execute(
                "SELECT * FROM rag_documents WHERE doc_type = ? ORDER BY created_at DESC",
                (doc_type,),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute("SELECT * FROM rag_documents ORDER BY created_at DESC") as cur:
                rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def delete_rag_document(record_id: int) -> bool:
    async with _connect() as db:
        cur = await db.execute("DELETE FROM rag_documents WHERE id = ?", (record_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Resume Matches ────────────────────────────────────────────────────────────


async def save_resume_match(
    job_text: str,
    job_url: str | None,
    user_cv: str,
    gap_analysis: str,
    answer_strategy: str,
    match_score: int,
) -> int:
    async with _connect() as db:
        cur = await db.execute(
            """
            INSERT INTO resume_matches
                (job_text, job_url, user_cv, gap_analysis, answer_strategy, match_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (job_text, job_url, user_cv, gap_analysis, answer_strategy, match_score),
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


async def list_resume_matches() -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM resume_matches ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_resume_match(record_id: int) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM resume_matches WHERE id = ?", (record_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def delete_resume_match(record_id: int) -> bool:
    async with _connect() as db:
        cur = await db.execute("DELETE FROM resume_matches WHERE id = ?", (record_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Mock Interviews ────────────────────────────────────────────────────────────


async def save_mock_interview(
    job_text: str,
    technical_questions: list[str],
    behavioral_questions: list[str],
    tips: str,
) -> int:
    async with _connect() as db:
        cur = await db.execute(
            """
            INSERT INTO mock_interviews
                (job_text, technical_questions, behavioral_questions, tips)
            VALUES (?, ?, ?, ?)
            """,
            (
                job_text,
                json.dumps(technical_questions, ensure_ascii=False),
                json.dumps(behavioral_questions, ensure_ascii=False),
                tips,
            ),
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


async def list_mock_interviews() -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mock_interviews ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_mock_interview(record_id: int) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mock_interviews WHERE id = ?", (record_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def delete_mock_interview(record_id: int) -> bool:
    async with _connect() as db:
        cur = await db.execute("DELETE FROM mock_interviews WHERE id = ?", (record_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Jobs on the kanban (/api/applications) ────────────────────────────────────

_APP_FIELDS = ("url", "job", "company", "city", "salary", "date", "status")


async def insert_applications(items: list[dict]) -> None:
    """Put jobs on the kanban. Rows already on it are untouched; off-board rows
    (removed earlier, or created by the liveness check) are restored."""
    updates = ", ".join(f"{f} = excluded.{f}" for f in _APP_FIELDS[1:])
    async with _connect() as db:
        await db.executemany(
            f"INSERT INTO jobs ({', '.join(_APP_FIELDS)}) "
            f"VALUES ({', '.join('?' * len(_APP_FIELDS))}) "
            f"ON CONFLICT(url) DO UPDATE SET {updates}, "
            "status_changed_at = datetime('now','localtime') "
            "WHERE jobs.status IS NULL",
            [tuple(i[f] for f in _APP_FIELDS) for i in items],
        )
        await db.commit()


async def list_applications() -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM jobs WHERE status IS NOT NULL ORDER BY created_at DESC, id DESC"
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def update_application_status(url: str, status: str) -> bool:
    async with _connect() as db:
        # RHS sees the pre-update row, so the timestamp only moves on a real change.
        cur = await db.execute(
            """
            UPDATE jobs SET
                status_changed_at = CASE WHEN status != ?
                    THEN datetime('now','localtime') ELSE status_changed_at END,
                status = ?
            WHERE url = ? AND status IS NOT NULL
            """,
            (status, status, url),
        )
        await db.commit()
        return cur.rowcount > 0


async def unboard_application(url: str) -> bool:
    """Take a job off the kanban. The row stays: liveness (and later job_id refs) use it."""
    async with _connect() as db:
        cur = await db.execute(
            "UPDATE jobs SET status = NULL, status_changed_at = datetime('now','localtime')"
            " WHERE url = ? AND status IS NOT NULL",
            (url,),
        )
        await db.commit()
        return cur.rowcount > 0
