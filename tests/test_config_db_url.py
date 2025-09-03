import importlib
import os

import app.config as config


def test_placeholder_database_url(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5432/whatever",
    )
    importlib.reload(config)
    assert (
        config.CONFIG.database_url
        == "postgresql+psycopg:///message_automation"
    )
    monkeypatch.delenv("DATABASE_URL")
