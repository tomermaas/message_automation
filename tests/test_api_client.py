import httpx
import pytest

from automation import api_client

@pytest.mark.asyncio
async def test_login_parses_response():
    expected = {"status": True, "token": "abc123", "data": {"id": 42, "name": "Teacher"}}

    async def handler(request):
        assert request.url.path == "/api/client-login"
        return httpx.Response(200, json=expected)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await api_client.login("user", "pass", client=client)

    assert result["token"] == expected["token"]
    assert result["teacher_id"] == expected["data"]["id"]
    assert result["display_name"] == expected["data"]["name"]


@pytest.mark.asyncio
async def test_session_helpers():
    login_payload = {"status": True, "token": "tkn", "data": {"id": 7, "name": "T"}}
    courses_payload = {"status": True, "data": [{"course_id": 1, "name": "Math"}]}
    dist_payload = {"status": True, "data": [{"student_id": "s1"}]}

    async def handler(request):
        if request.url.path == "/api/client-login":
            return httpx.Response(200, json=login_payload)
        if request.url.path == "/api/get-courses":
            return httpx.Response(200, json=courses_payload)
        if request.url.path == "/api/get-distance-details":
            return httpx.Response(200, json=dist_payload)
        raise AssertionError(f"unexpected path: {request.url.path}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        sess = api_client.KidumApiSession(client)
        assert await sess.login("u", "p")
        courses = await sess.api_get_courses()
        assert courses == courses_payload["data"]
        dist = await sess.api_get_distance_details(1)
        assert dist == dist_payload["data"]


@pytest.mark.asyncio
async def test_distance_details_nested_structure():
    """The distance details endpoint may wrap the list in a nested object."""
    login_payload = {"status": True, "token": "tok", "data": {"id": 9, "name": "T"}}
    nested_payload = {"status": True, "data": {"rows": [{"student_id": "s1"}]}}

    async def handler(request):
        if request.url.path == "/api/client-login":
            return httpx.Response(200, json=login_payload)
        if request.url.path == "/api/get-distance-details":
            return httpx.Response(200, json=nested_payload)
        raise AssertionError(f"unexpected path: {request.url.path}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        sess = api_client.KidumApiSession(client)
        assert await sess.login("u", "p")
        dist = await sess.api_get_distance_details(1)
    assert dist == nested_payload["data"]["rows"]


@pytest.mark.asyncio
async def test_distance_details_merges_multiple_lists():
    """Multiple list values should be combined (new and updated entries)."""
    login_payload = {"status": True, "token": "tok", "data": {"id": 9, "name": "T"}}
    multi_payload = {
        "status": True,
        "data": {
            "new": [{"student_id": "s0"}],
            "updated": [{"student_id": "s1"}],
        },
    }

    async def handler(request):
        if request.url.path == "/api/client-login":
            return httpx.Response(200, json=login_payload)
        if request.url.path == "/api/get-distance-details":
            return httpx.Response(200, json=multi_payload)
        raise AssertionError(f"unexpected path: {request.url.path}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        sess = api_client.KidumApiSession(client)
        assert await sess.login("u", "p")
        dist = await sess.api_get_distance_details(1)
    assert dist == multi_payload["data"]["new"] + multi_payload["data"]["updated"]


@pytest.mark.asyncio
async def test_distance_details_handles_nested_lists():
    """Lists nested inside objects (e.g. ``{"new": {"rows": [...]}}``) are flattened."""
    login_payload = {"status": True, "token": "tok", "data": {"id": 9, "name": "T"}}
    nested_lists_payload = {
        "status": True,
        "data": {
            "new": {"rows": [{"student_id": "s0"}]},
            "updated": {"rows": [{"student_id": "s1"}]},
        },
    }

    async def handler(request):
        if request.url.path == "/api/client-login":
            return httpx.Response(200, json=login_payload)
        if request.url.path == "/api/get-distance-details":
            return httpx.Response(200, json=nested_lists_payload)
        raise AssertionError(f"unexpected path: {request.url.path}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        sess = api_client.KidumApiSession(client)
        assert await sess.login("u", "p")
        dist = await sess.api_get_distance_details(1)
    expected = (
        nested_lists_payload["data"]["new"]["rows"]
        + nested_lists_payload["data"]["updated"]["rows"]
    )
    assert dist == expected
