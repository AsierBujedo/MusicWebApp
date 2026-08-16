"""Pytest fixtures: a fresh in-memory-ish app + authenticated clients.

Each test module gets its own SQLite file and a TestClient with the request
worker running. The dev admin (admin/admin) is auto-seeded by bootstrap.
"""
from __future__ import annotations

import os
import tempfile

import pytest

os.environ["MOCK_EXTERNAL_SERVICES"] = "true"
os.environ["APP_ENV"] = "development"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["REQUEST_POLL_INTERVAL_SECONDS"] = "1"
# Force same-origin cookie policy (SameSite=Lax, non-Secure) so the ASGI
# TestClient's cookie jar stores the session cookie over plain http. The
# project injects FRONTEND_ORIGIN, which would otherwise flip cookies to
# SameSite=None; Secure and break the in-process HTTP test transport.
os.environ["FRONTEND_ORIGIN"] = ""

# Point the DB at a throwaway file before importing the app/config.
_TMP_DB = os.path.join(tempfile.gettempdir(), "hma_test.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_client(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert r.status_code == 200, r.text
    yield client
    client.post("/api/auth/logout")
