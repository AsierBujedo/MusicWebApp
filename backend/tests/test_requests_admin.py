from __future__ import annotations

import time


def _requestable_track(admin_client):
    tracks = admin_client.get("/api/search", params={"q": "This Is America"}).json()["tracks"]
    return next(t for t in tracks if t["status"] == "REQUESTABLE")


def test_request_lifecycle_reaches_available(admin_client):
    track = _requestable_track(admin_client)
    created = admin_client.post("/api/requests", json={"type": "track", "trackId": track["id"]})
    assert created.status_code == 201
    req = created.json()
    assert req["status"] == "PENDING"
    assert req["trackId"] == track["id"]
    rid = req["id"]

    # admin approves; worker drives it to AVAILABLE
    assert admin_client.post(f"/api/admin/requests/{rid}/approve").status_code == 200

    final = None
    for _ in range(40):
        time.sleep(1)
        cur = admin_client.get(f"/api/requests/{rid}").json()
        if cur["status"] in ("AVAILABLE", "FAILED"):
            final = cur["status"]
            break
    assert final == "AVAILABLE"

    # the track should now be AVAILABLE in the library
    t = admin_client.get(f"/api/tracks/{track['id']}").json()
    assert t["status"] == "AVAILABLE"


def test_available_track_cannot_be_requested(admin_client):
    tracks = admin_client.get("/api/search", params={"q": "daft"}).json()["tracks"]
    avail = next(t for t in tracks if t["status"] == "AVAILABLE")
    r = admin_client.post("/api/requests", json={"type": "track", "trackId": avail["id"]})
    assert r.status_code == 409


def test_reject_then_retry(admin_client):
    track = _requestable_track(admin_client)
    # ensure a clean pending request (dedup returns existing active one)
    req = admin_client.post("/api/requests", json={"type": "track", "trackId": track["id"]}).json()
    rid = req["id"]
    admin_client.post(f"/api/admin/requests/{rid}/reject")
    cur = admin_client.get(f"/api/requests/{rid}").json()
    assert cur["status"] == "REJECTED"
    retried = admin_client.post(f"/api/requests/{rid}/retry")
    assert retried.status_code == 200
    assert retried.json()["status"] == "PENDING"


def test_admin_stats_and_services(admin_client):
    stats = admin_client.get("/api/admin/stats").json()
    for key in ("users", "requests", "availableTracks"):
        assert key in stats
    services = admin_client.get("/api/admin/services").json()
    keys = {s["key"] for s in services}
    assert {"navidrome", "droppedneedle", "slskd"} <= keys
    for s in services:
        assert s["status"] in {"online", "degraded", "offline"}


def test_admin_user_management_and_last_admin_guard(admin_client):
    created = admin_client.post(
        "/api/admin/users",
        json={"username": "alice", "password": "password1", "displayName": "Alice", "role": "USER"},
    )
    assert created.status_code == 201
    uid = created.json()["id"]
    assert created.json()["role"] == "USER"

    patched = admin_client.patch(f"/api/admin/users/{uid}", json={"role": "ADMIN"})
    assert patched.status_code == 200
    assert patched.json()["role"] == "ADMIN"

    assert admin_client.delete(f"/api/admin/users/{uid}").status_code == 204

    # cannot delete the final remaining admin (self)
    me = admin_client.get("/api/auth/me").json()
    guard = admin_client.delete(f"/api/admin/users/{me['id']}")
    assert guard.status_code == 400


def test_non_admin_forbidden(client):
    client.cookies.clear()
    # create a normal user via admin, then log in as them
    client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    client.post(
        "/api/admin/users",
        json={"username": "bob", "password": "password1", "displayName": "Bob", "role": "USER"},
    )
    client.post("/api/auth/logout")
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "bob", "password": "password1"})
    r = client.get("/api/admin/stats")
    assert r.status_code == 403
    client.post("/api/auth/logout")
