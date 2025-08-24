import os
import sqlite3
import pytest

pytest.importorskip("playwright.async_api")

from automation.browser_async import AsyncKidumSession
from app.services.distance_syncer import DistanceSyncer


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_BROWSER_TEST"),
    reason="requires network access and real credentials",
)
async def test_distance_db_matches_remote(tmp_path):
    username = os.getenv("KIDUM_USERNAME")
    password = os.getenv("KIDUM_PASSWORD")
    if not username or not password:
        pytest.skip("KIDUM_USERNAME and KIDUM_PASSWORD required")

    session = AsyncKidumSession(headless=True)
    try:
        assert await session.login(username, password)
        courses = await session.api_get_courses()
        if not courses:
            pytest.skip("no courses returned")
        course = courses[0]
        course_id = course.get("course_id") or course.get("id")
        if course_id is None:
            pytest.skip("course id missing in API data")
        course_id = int(course_id)

        syncer = DistanceSyncer(tmp_path)
        await syncer.sync_and_collect(session, course_id)
        remote_rows = await session.api_get_distance_details(course_id)

        db_path = tmp_path / "courses" / str(course_id) / "distance.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM distance").fetchall()
        conn.close()
        local_by_id = {row["student_id"]: row for row in rows}

        assert set(local_by_id.keys()) == {r["student_id"] for r in remote_rows}

        for r in remote_rows:
            local = local_by_id[r["student_id"]]
            common = set(local.keys()) & set(r.keys())
            for col in common:
                assert str(local[col]) == str(r[col])
    finally:
        await session.close()
