"""Test setup: a throwaway database, a known API key, and a fake AI."""

import os
import tempfile

_tmpdir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["API_KEY"] = "test-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import ai  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

HEADERS = {"X-API-Key": "test-key"}


class FakeAI:
    """Stands in for the real model. Queue up replies; it records each call."""

    def __init__(self):
        self.replies: list[ai.Extraction] = []
        self.calls: list[dict] = []

    def __call__(self, raw_input, clarifications, now_local, allow_question):
        self.calls.append(
            {"raw_input": raw_input, "clarifications": list(clarifications), "allow_question": allow_question}
        )
        return self.replies.pop(0)


@pytest.fixture
def fake_ai(monkeypatch):
    fake = FakeAI()
    monkeypatch.setattr(ai, "extract_task", fake)
    return fake


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c
