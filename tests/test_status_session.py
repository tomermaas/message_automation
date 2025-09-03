from fastapi.testclient import TestClient
import app.webapp as webapp

class DummySession:
    def __init__(self):
        self.closed = False
    async def close(self):
        self.closed = True
    def get_logged_in_display_name(self):
        return None
    def get_teacher_id(self):
        return None
    def get_selected_course_id(self):
        return None


def test_status_reports_logged_out_for_partial_session():
    dummy = DummySession()
    webapp._session = dummy
    client = TestClient(webapp.app)
    status = client.get('/status').json()
    assert status == {
        'ok': True,
        'logged_in': False,
        'display_name': None,
        'teacher_id': None,
        'selected_id': None,
    }
    client.post('/logout')
    assert dummy.closed is True
    assert webapp._session is None


class NamelessSession:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True

    def get_logged_in_display_name(self):
        return None

    def get_teacher_id(self):
        return 1

    def get_selected_course_id(self):
        return None


def test_status_logged_in_without_display_name():
    dummy = NamelessSession()
    webapp._session = dummy
    client = TestClient(webapp.app)
    status = client.get('/status').json()
    assert status == {
        'ok': True,
        'logged_in': True,
        'display_name': None,
        'teacher_id': 1,
        'selected_id': None,
    }
    client.post('/logout')
    assert dummy.closed is True
    assert webapp._session is None
