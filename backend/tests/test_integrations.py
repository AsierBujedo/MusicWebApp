"""Integration-adapter tests.

These exercise the real adapters against a mocked ``httpx`` transport, so no
external DroppedNeedle / Navidrome / slskd is required. They verify the exact
contract the adapters depend on:

- DroppedNeedle: login -> bearer token, search mapping, request by musicbrainz_id,
  401 -> automatic re-login -> retry, and active/downloads status sync.
- Navidrome: Subsonic ping/search over token auth.
- slskd: health via X-API-Key.
"""
from __future__ import annotations

import json

import httpx
import pytest


def _make_dn_client(handler):
    """Build a RealDroppedNeedleClient whose AsyncClient uses a MockTransport."""
    from app.services.integrations import droppedneedle as dn_mod

    client = dn_mod.RealDroppedNeedleClient()
    client._username = "svc"
    client._password = "secret"
    transport = httpx.MockTransport(handler)
    # Replace the outbound client with one backed by our mock transport.
    client._client = httpx.AsyncClient(base_url="http://droppedneedle:8000", transport=transport)
    return client


@pytest.mark.asyncio
async def test_droppedneedle_login_and_search():
    calls = {"login": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            calls["login"] += 1
            body = json.loads(request.content)
            assert body["username"] == "svc" and body["password"] == "secret"
            return httpx.Response(200, json={"token": "tok-123", "user": {"username": "svc"}})
        if request.url.path == "/api/v1/search":
            # Must carry the bearer token obtained from login.
            assert request.headers.get("Authorization") == "Bearer tok-123"
            return httpx.Response(
                200,
                json={
                    "albums": [
                        {
                            "type": "album",
                            "title": "Homework",
                            "artist": "Daft Punk",
                            "musicbrainz_id": "mbid-1",
                            "in_library": False,
                            "requested": False,
                            "cover_url": "http://x/cover.jpg",
                            "year": 1997,
                        },
                        {
                            "title": "Discovery",
                            "artist": "Daft Punk",
                            "musicbrainz_id": "mbid-2",
                            "in_library": True,
                            "requested": False,
                        },
                    ],
                    "artists": [
                        {"title": "Daft Punk", "musicbrainz_id": "mbid-art", "thumb_url": "http://x/a.jpg"}
                    ],
                },
            )
        return httpx.Response(404)

    client = _make_dn_client(handler)
    try:
        result = await client.search("daft", 10)
    finally:
        await client.aclose()

    assert calls["login"] == 1
    assert len(result.albums) == 2
    homework = next(a for a in result.albums if a.musicbrainz_id == "mbid-1")
    discovery = next(a for a in result.albums if a.musicbrainz_id == "mbid-2")
    assert homework.available is False  # in_library=False
    assert discovery.available is True  # in_library=True
    assert result.artists[0].name == "Daft Punk"


@pytest.mark.asyncio
async def test_droppedneedle_request_uses_musicbrainz_id():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"token": "tok", "user": {}})
        if request.url.path == "/api/v1/requests/new":
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json={"id": "task-99"})
        return httpx.Response(404)

    client = _make_dn_client(handler)
    try:
        res = await client.request(type="album", title="Homework", artist="Daft Punk", musicbrainz_id="mbid-1")
    finally:
        await client.aclose()

    assert res["accepted"] is True
    assert res["external_id"] == "task-99"
    assert seen["body"]["musicbrainz_id"] == "mbid-1"


@pytest.mark.asyncio
async def test_droppedneedle_request_without_mbid_is_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"token": "tok", "user": {}})
        raise AssertionError("must not call requests/new without a musicbrainz_id")

    client = _make_dn_client(handler)
    try:
        res = await client.request(type="album", title="X", artist="Y", musicbrainz_id=None)
    finally:
        await client.aclose()
    assert res["accepted"] is False


@pytest.mark.asyncio
async def test_droppedneedle_relogins_on_401():
    state = {"logins": 0, "search_calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            state["logins"] += 1
            return httpx.Response(200, json={"token": f"tok-{state['logins']}", "user": {}})
        if request.url.path == "/api/v1/search":
            state["search_calls"] += 1
            # First search (with the stale token) is rejected; the retry succeeds.
            if state["search_calls"] == 1:
                return httpx.Response(401, json={"detail": "expired"})
            assert request.headers.get("Authorization") == "Bearer tok-2"
            return httpx.Response(200, json={"albums": [], "artists": []})
        return httpx.Response(404)

    client = _make_dn_client(handler)
    # Seed a stale token so the first call triggers the 401 path.
    client._token = "tok-stale"
    try:
        result = await client.search("q", 5)
    finally:
        await client.aclose()

    assert state["logins"] == 1  # re-login happened exactly once
    assert state["search_calls"] == 2  # original + retry
    assert result.albums == []


@pytest.mark.asyncio
async def test_droppedneedle_sync_status_maps_states():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"token": "tok", "user": {}})
        if request.url.path == "/api/v1/requests/active":
            return httpx.Response(
                200,
                json=[
                    {"musicbrainz_id": "mbid-a", "status": "downloading", "progress": 40},
                    {"musicbrainz_id": "mbid-b", "status": "completed"},
                ],
            )
        if request.url.path == "/api/v1/downloads":
            return httpx.Response(200, json=[{"musicbrainz_id": "mbid-a", "progress": 55}])
        return httpx.Response(404)

    client = _make_dn_client(handler)
    try:
        status_map = await client.sync_status()
    finally:
        await client.aclose()

    assert status_map["mbid-a"]["status"] == "DOWNLOADING"
    assert status_map["mbid-a"]["progress"] == 55  # downloads override refines progress
    assert status_map["mbid-b"]["status"] == "AVAILABLE"


@pytest.mark.asyncio
async def test_navidrome_health_and_search():
    from app.services.integrations import navidrome as nav_mod

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ping.view"):
            return httpx.Response(200, json={"subsonic-response": {"status": "ok"}})
        if request.url.path.endswith("/search3.view"):
            return httpx.Response(
                200,
                json={
                    "subsonic-response": {
                        "searchResult3": {
                            "song": [
                                {"id": "s1", "title": "One More Time", "artist": "Daft Punk", "album": "Discovery"}
                            ],
                            "album": [],
                            "artist": [],
                        }
                    }
                },
            )
        return httpx.Response(404)

    client = nav_mod.RealNavidromeClient()
    client._username = "admin"
    client._password = "pw"
    client._base = "http://navidrome:4533"
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        status, _ = await client.health()
        results = await client.search("daft", 10)
    finally:
        await client.aclose()

    assert status == "online"
    assert results.tracks[0].title == "One More Time"
    assert results.tracks[0].available is True


@pytest.mark.asyncio
async def test_slskd_health_uses_api_key():
    from app.services.integrations import slskd as slskd_mod

    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["key"] = request.headers.get("X-API-Key")
        return httpx.Response(200, text="Healthy")

    client = slskd_mod.RealSlskdClient()
    client._client = httpx.AsyncClient(
        base_url="http://slskd:5030",
        headers={"X-API-Key": "slskd-key"},
        transport=httpx.MockTransport(handler),
    )
    try:
        status, _ = await client.health()
    finally:
        await client.aclose()

    assert status == "online"
    assert seen["key"] == "slskd-key"


def test_health_probe_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
