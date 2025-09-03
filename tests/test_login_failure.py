from fastapi.testclient import TestClient
import app.webapp as webapp


class DummySession:
    def __init__(self, ok=False):
        self.ok = ok
        self.closed = False

    async def login(self, username: str, password: str) -> bool:
        return self.ok

    async def close(self):
        self.closed = True

    def get_logged_in_display_name(self):
        return "dummy"

    def get_teacher_id(self):
        return 0


def test_failed_login_clears_session(monkeypatch):
    dummy = DummySession(ok=False)
    # Patch KidumApiSession to return our dummy session
    monkeypatch.setattr(webapp, "KidumApiSession", lambda: dummy)
    client = TestClient(webapp.app)

    # Attempt login with bad credentials
    res = client.post("/login", json={"username": "bad", "password": "bad"})
    assert res.status_code == 401
    assert webapp._session is None
    assert dummy.closed is True

    # Status endpoint should report logged_in=False
    status = client.get("/status").json()
    assert status["logged_in"] is False
