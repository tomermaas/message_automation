import base64
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
