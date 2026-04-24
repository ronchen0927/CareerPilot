import json
from pathlib import Path

import aiosqlite

from .config import settings

_DB_PATH: Path | None = None


def _db_path() -> Path:
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = Path(settings.DB_PATH)
    return _DB_PATH


async def init_db() -> None:
    async with aiosqlite.connect(_db_path()) as db:
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
            CREATE TABLE IF NOT EXISTS job_liveness (
                job_url      TEXT    PRIMARY KEY,
                status       TEXT    NOT NULL DEFAULT 'unknown',
                last_checked TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                last_reason  TEXT,
                fail_count   INTEGER NOT NULL DEFAULT 0
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
        await db.commit()


async def get_evaluation(record_id: int) -> dict | None:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM evaluations WHERE id = ?", (record_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def get_cached(job_hash: str) -> dict | None:
    async with aiosqlite.connect(_db_path()) as db:
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
    async with aiosqlite.connect(_db_path()) as db:
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


async def list_evaluations() -> list[dict]:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM evaluations ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def delete_evaluation(record_id: int) -> bool:
    async with aiosqlite.connect(_db_path()) as db:
        cur = await db.execute("DELETE FROM evaluations WHERE id = ?", (record_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Cover letters ─────────────────────────────────────────────────────────────


async def save_cover_letter(job_text: str, letter: str) -> int:
    async with aiosqlite.connect(_db_path()) as db:
        cur = await db.execute(
            "INSERT INTO cover_letters (job_text, letter) VALUES (?, ?)",
            (job_text, letter),
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


async def list_cover_letters() -> list[dict]:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM cover_letters ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_cover_letter(record_id: int) -> dict | None:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM cover_letters WHERE id = ?", (record_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def delete_cover_letter(record_id: int) -> bool:
    async with aiosqlite.connect(_db_path()) as db:
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
    async with aiosqlite.connect(_db_path()) as db:
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
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM resume_rewrites ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_resume_rewrite(record_id: int) -> dict | None:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM resume_rewrites WHERE id = ?", (record_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def delete_resume_rewrite(record_id: int) -> bool:
    async with aiosqlite.connect(_db_path()) as db:
        cur = await db.execute("DELETE FROM resume_rewrites WHERE id = ?", (record_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Job liveness ──────────────────────────────────────────────────────────────


async def upsert_liveness(job_url: str, status: str, reason: str | None, fail_count: int) -> None:
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            """
            INSERT INTO job_liveness (job_url, status, last_reason, fail_count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(job_url) DO UPDATE SET
                status       = excluded.status,
                last_checked = datetime('now','localtime'),
                last_reason  = excluded.last_reason,
                fail_count   = excluded.fail_count
            """,
            (job_url, status, reason, fail_count),
        )
        await db.commit()


async def get_liveness_map(urls: list[str]) -> dict[str, dict]:
    if not urls:
        return {}
    placeholders = ",".join("?" * len(urls))
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"SELECT * FROM job_liveness WHERE job_url IN ({placeholders})",
            urls,  # noqa: S608
        ) as cur:
            rows = await cur.fetchall()
    return {r["job_url"]: dict(r) for r in rows}


async def get_liveness_fail_count(job_url: str) -> int:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT fail_count FROM job_liveness WHERE job_url = ?", (job_url,)
        ) as cur:
            row = await cur.fetchone()
    return row["fail_count"] if row else 0


async def list_liveness_targets() -> list[str]:
    """Return distinct job_url values from evaluated jobs."""
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT DISTINCT job_url FROM evaluations WHERE job_url IS NOT NULL"
        ) as cur:
            rows = await cur.fetchall()
    return [r["job_url"] for r in rows]


# ── RAG Documents ─────────────────────────────────────────────────────────────


async def save_rag_document(doc_type: str, content: str, embedding: list[float]) -> int:
    async with aiosqlite.connect(_db_path()) as db:
        cur = await db.execute(
            "INSERT INTO rag_documents (doc_type, content, embedding) VALUES (?, ?, ?)",
            (doc_type, content, json.dumps(embedding)),
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


async def list_rag_documents(doc_type: str | None = None) -> list[dict]:
    async with aiosqlite.connect(_db_path()) as db:
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
    async with aiosqlite.connect(_db_path()) as db:
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
    async with aiosqlite.connect(_db_path()) as db:
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
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM resume_matches ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_resume_match(record_id: int) -> dict | None:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM resume_matches WHERE id = ?", (record_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def delete_resume_match(record_id: int) -> bool:
    async with aiosqlite.connect(_db_path()) as db:
        cur = await db.execute("DELETE FROM resume_matches WHERE id = ?", (record_id,))
        await db.commit()
        return cur.rowcount > 0
