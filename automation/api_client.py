from __future__ import annotations

import httpx
from typing import Any, Dict, Optional, List

from app.config import CONFIG

async def login(username: str, password: str, client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:
    """Authenticate against the Kidum LMS API.

    Parameters
    ----------
    username: str
        Login identifier passed to the ``user_id`` field of the API.
    password: str
        Password for the account.
    client: httpx.AsyncClient, optional
        Optional client to reuse across calls, mainly for testing.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing the ``token`` string, ``teacher_id`` integer and
        optional ``display_name`` if provided by the API.

    Raises
    ------
    httpx.HTTPStatusError
        If the API returns a non-success status code.
    ValueError
        If the expected fields are missing from the response payload.
    """

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=20.0)
        close_client = True

    try:
        url = f"{CONFIG.api_base_url}/api/client-login"
        payload = {"user_id": username, "password": password}
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

        token = data.get("token")
        user_data = data.get("data", {})
        teacher_id = user_data.get("id")
        display_name = (
            user_data.get("name")
            or user_data.get("full_name")
            or (f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip() or None)
        )

        if not token or teacher_id is None:
            raise ValueError("token or teacher_id missing in response")

        return {"token": token, "teacher_id": teacher_id, "display_name": display_name}
    finally:
        if close_client:
            await client.aclose()


class KidumApiSession:
    """Minimal asynchronous session for interacting with the Kidum LMS API.

    The session stores the authentication token and teacher id returned from
    :func:`login` and exposes helper methods for subsequent API calls.  Only a
    subset of endpoints required by the application are implemented.
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=20.0)
        self._owns_client = client is None
        self._token: Optional[str] = None
        self._teacher_id: Optional[int] = None
        self._display_name: Optional[str] = None
        self._selected_course_id: Optional[int] = None

    async def login(self, username: str, password: str) -> bool:
        try:
            data = await login(username, password, self._client)
        except Exception:
            return False
        self._token = data["token"]
        self._teacher_id = data["teacher_id"]
        self._display_name = data.get("display_name")
        return True

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def get_logged_in_display_name(self) -> Optional[str]:
        return self._display_name

    def get_teacher_id(self) -> Optional[int]:
        return self._teacher_id

    def set_selected_course_id(self, course_id: int | None) -> None:
        self._selected_course_id = int(course_id) if course_id is not None else None

    def get_selected_course_id(self) -> Optional[int]:
        return self._selected_course_id

    async def api_get_courses(self) -> List[Dict[str, Any]]:
        if not self._token or self._teacher_id is None:
            raise RuntimeError("Not logged in")
        url = f"{CONFIG.api_base_url}/api/get-courses?teacher_id={self._teacher_id}"
        headers = {"Authorization": f"Bearer {self._token}"}
        r = await self._client.get(url, headers=headers)
        r.raise_for_status()
        payload = r.json()
        if isinstance(payload, dict) and payload.get("status") and isinstance(payload.get("data"), list):
            return payload["data"]
        return []

    async def api_get_distance_details(self, course_id: int):
        if not self._token or self._teacher_id is None:
            raise RuntimeError("Not logged in")
        url = (
            f"{CONFIG.api_base_url}/api/get-distance-details?teacher_id={self._teacher_id}&course_id={course_id}"
        )
        headers = {"Authorization": f"Bearer {self._token}"}
        r = await self._client.get(url, headers=headers)
        r.raise_for_status()
        payload = r.json()
        if not payload.get("status"):
            raise RuntimeError(f"Distance API error: {payload}")
        return payload.get("data", [])
