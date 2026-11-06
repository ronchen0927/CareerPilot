"""#50: list/get/delete behave the same for every history table."""

import asyncio

import pytest

from app import db

SAVERS = {
    "evaluations": lambda n: db.save_evaluation(f"h{n}", f"jd{n}", None, "A", "s", [], [], "r"),
    "cover_letters": lambda n: db.save_cover_letter(f"jd{n}", "letter"),
    "resume_rewrites": lambda n: db.save_resume_rewrite(f"jd{n}", None, "cv", "out"),
    "resume_matches": lambda n: db.save_resume_match(f"jd{n}", None, "cv", "gap", "strat", 80),
    "mock_interviews": lambda n: db.save_mock_interview(f"jd{n}", ["t"], ["b"], "tips"),
}
CRUD = {
    "evaluations": (db.list_evaluations, db.get_evaluation, db.delete_evaluation),
    "cover_letters": (db.list_cover_letters, db.get_cover_letter, db.delete_cover_letter),
    "resume_rewrites": (db.list_resume_rewrites, db.get_resume_rewrite, db.delete_resume_rewrite),
    "resume_matches": (db.list_resume_matches, db.get_resume_match, db.delete_resume_match),
    "mock_interviews": (db.list_mock_interviews, db.get_mock_interview, db.delete_mock_interview),
}


@pytest.mark.parametrize("table", CRUD)
def test_list_get_delete(table, db_file):
    list_, get, delete = CRUD[table]

    async def run():
        await db.init_db()
        first = await SAVERS[table](1)
        second = await SAVERS[table](2)

        rows = await list_()
        assert {r["id"] for r in rows} == {first, second}
        assert (await get(first))["job_text"] == "jd1"
        assert await get(999) is None

        assert await delete(first) is True
        assert await delete(first) is False
        assert await get(first) is None
        assert [r["id"] for r in await list_()] == [second]

    asyncio.run(run())


def test_unknown_table_is_rejected(db_file):
    with pytest.raises(ValueError):
        asyncio.run(db._get("sqlite_master", 1))
