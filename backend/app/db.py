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
) -> int:
    async with aiosqlite.connect(_db_path()) as db:
        cur = await db.execute(
            """
            INSERT INTO evaluations
                (job_hash, job_text, job_url, score, summary,
                 match_points, gap_points, recommendation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
