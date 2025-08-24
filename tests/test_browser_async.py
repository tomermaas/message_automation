import base64
import os
import pytest

pytest.importorskip("playwright.async_api")
from automation.browser_async import AsyncKidumSession


def test_jwt_helpers():
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b'=').decode()
    payload = base64.urlsafe_b64encode(b'{"sub":"123"}').rstrip(b'=').decode()
    sig = base64.urlsafe_b64encode(b'sig').rstrip(b'=').decode()
    token = f"{header}.{payload}.{sig}"

    assert AsyncKidumSession._looks_like_jwt(token)
    session = AsyncKidumSession()
    assert session._decode_jwt_sub(token) == "123"

    assert not AsyncKidumSession._looks_like_jwt("not a token")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_BROWSER_TEST"),
    reason="requires network access and real credentials",
)
async def test_login_and_fetch_courses():
    session = AsyncKidumSession(headless=True)
    try:
        assert await session.login("311550651", "311550651")
        courses = await session.api_get_courses()
        assert isinstance(courses, list)
    finally:
        await session.close()
