from __future__ import annotations


def _first_track(admin_client, q="daft"):
    r = admin_client.get("/api/search", params={"q": q})
    assert r.status_code == 200
    return r.json()["tracks"][0]


def test_search_shape(admin_client):
    r = admin_client.get("/api/search", params={"q": "daft"})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"tracks", "albums", "artists"}
    t = body["tracks"][0]
    # camelCase contract fields present
    for key in ("id", "title", "artist", "status"):
        assert key in t
    assert t["status"] in {"AVAILABLE", "REQUESTABLE", "PENDING", "DOWNLOADING"}


def test_short_query_returns_empty(admin_client):
    r = admin_client.get("/api/search", params={"q": "a"})
    assert r.status_code == 200
    assert r.json() == {"tracks": [], "albums": [], "artists": []}


def test_favorites_add_list_remove(admin_client):
    t = _first_track(admin_client)
    tid = t["id"]
    assert admin_client.post(f"/api/favorites/{tid}").status_code == 204
    favs = admin_client.get("/api/favorites").json()
    assert any(f["id"] == tid for f in favs)
    assert admin_client.delete(f"/api/favorites/{tid}").status_code == 204
    favs = admin_client.get("/api/favorites").json()
    assert not any(f["id"] == tid for f in favs)


def test_history_record_and_list(admin_client):
    t = _first_track(admin_client)
    assert admin_client.post("/api/history", json={"trackId": t["id"]}).status_code == 204
    hist = admin_client.get("/api/history").json()
    # HistoryEntry contract: { track, playedAt }
    assert any(h["track"]["id"] == t["id"] for h in hist)
    assert all("playedAt" in h for h in hist)


def test_playlist_crud_and_reorder(admin_client):
    created = admin_client.post("/api/playlists", json={"name": "Roadtrip"})
    assert created.status_code == 201
    pl = created.json()
    pid = pl["id"]
    assert pl["name"] == "Roadtrip"
    assert pl["tracks"] == []

    tracks = admin_client.get("/api/search", params={"q": "daft"}).json()["tracks"]
    t1, t2 = tracks[0]["id"], tracks[1]["id"]
    admin_client.post(f"/api/playlists/{pid}/tracks", json={"trackId": t1})
    updated = admin_client.post(f"/api/playlists/{pid}/tracks", json={"trackId": t2}).json()
    assert [t["id"] for t in updated["tracks"]] == [t1, t2]

    reordered = admin_client.post(f"/api/playlists/{pid}/reorder", json={"trackIds": [t2, t1]}).json()
    assert [t["id"] for t in reordered["tracks"]] == [t2, t1]

    admin_client.delete(f"/api/playlists/{pid}/tracks/{t1}")
    after = admin_client.get("/api/playlists").json()
    target = next(p for p in after if p["id"] == pid)
    assert [t["id"] for t in target["tracks"]] == [t2]

    assert admin_client.delete(f"/api/playlists/{pid}").status_code == 204


def test_stream_supports_range(admin_client):
    # find an available track and stream a byte range
    tracks = admin_client.get("/api/search", params={"q": "daft"}).json()["tracks"]
    avail = next(t for t in tracks if t["status"] == "AVAILABLE")
    r = admin_client.get(f"/api/stream/{avail['id']}", headers={"Range": "bytes=0-1023"})
    assert r.status_code in (200, 206)
    assert r.headers.get("accept-ranges") == "bytes"
