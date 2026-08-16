"""Ad-hoc end-to-end smoke test against the ASGI app (no network)."""
import os

os.environ.setdefault("MOCK_EXTERNAL_SERVICES", "true")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/smoke.db")
os.environ.setdefault("SECRET_KEY", "smoke")

# Fresh DB every run.
db_path = "./data/smoke.db"
if os.path.exists(db_path):
    os.remove(db_path)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def main():
    with TestClient(app) as c:
        # Unauthenticated is rejected.
        assert c.get("/api/auth/me").status_code == 401, "me should require auth"

        # Login as bootstrap admin.
        r = c.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        assert r.status_code == 200, r.text
        me = r.json()
        assert me["role"] == "ADMIN" and me["username"] == "admin", me
        print("login OK:", me)

        # Search.
        r = c.get("/api/search", params={"q": "daft"})
        assert r.status_code == 200, r.text
        results = r.json()
        assert results["tracks"], "expected tracks"
        # Find a requestable (not available) track.
        requestable = next((t for t in results["tracks"] if t["status"] != "AVAILABLE"), None)
        available = next((t for t in results["tracks"] if t["status"] == "AVAILABLE"), None)
        assert available, "expected an available track"
        print("search OK: tracks=%d albums=%d artists=%d" % (
            len(results["tracks"]), len(results["albums"]), len(results["artists"])) )

        # Favorites.
        assert c.post(f"/api/favorites/{available['id']}").status_code == 204
        favs = c.get("/api/favorites").json()
        assert any(t["id"] == available["id"] for t in favs), favs
        assert c.delete(f"/api/favorites/{available['id']}").status_code == 204
        print("favorites OK")

        # History.
        assert c.post("/api/history", json={"trackId": available["id"]}).status_code == 204
        hist = c.get("/api/history").json()
        assert hist and hist[0]["track"]["id"] == available["id"], hist
        assert "playedAt" in hist[0]
        print("history OK")

        # Playlists.
        pl = c.post("/api/playlists", json={"name": "Roadtrip", "description": "Vibes"}).json()
        assert pl["name"] == "Roadtrip" and pl["trackIds"] == [], pl
        pl = c.post(f"/api/playlists/{pl['id']}/tracks", json={"trackId": available["id"]}).json()
        assert pl["trackIds"] == [available["id"]], pl
        assert pl["tracks"][0]["id"] == available["id"]
        pl = c.delete(f"/api/playlists/{pl['id']}/tracks/{available['id']}").json()
        assert pl["trackIds"] == [], pl
        assert c.delete(f"/api/playlists/{pl['id']}").status_code == 204
        print("playlists OK")

        # Requests lifecycle.
        if requestable:
            req = c.post("/api/requests", json={"type": "track", "trackId": requestable["id"]}).json()
            assert req["status"] == "PENDING" and req["trackId"] == requestable["id"], req
            assert req["requestedByName"] == "Admin", req
            # Admin approve.
            approved = c.post(f"/api/admin/requests/{req['id']}/approve").json()
            assert approved["status"] == "APPROVED", approved
            # Admin listing includes requester name.
            all_reqs = c.get("/api/admin/requests").json()
            assert any(x["id"] == req["id"] for x in all_reqs), all_reqs
            print("requests OK:", req["id"])

        # Admin stats + services.
        stats = c.get("/api/admin/stats").json()
        assert set(stats.keys()) == {"users", "requests", "downloads", "availableTracks"}, stats
        services = c.get("/api/admin/services").json()
        assert {s["key"] for s in services} == {"navidrome", "droppedneedle", "slskd"}, services
        print("admin OK:", stats)

        # Admin user management.
        u = c.post("/api/admin/users", json={"username": "alice", "displayName": "Alice", "role": "USER"}).json()
        assert u["username"] == "alice" and u["role"] == "USER", u
        u = c.patch(f"/api/admin/users/{u['id']}", json={"active": False}).json()
        assert u["active"] is False, u
        assert c.delete(f"/api/admin/users/{u['id']}").status_code == 204
        print("user mgmt OK")

        # Cannot delete last admin.
        admins = [x for x in c.get("/api/admin/users").json() if x["role"] == "ADMIN"]
        r = c.delete(f"/api/admin/users/{admins[0]['id']}")
        assert r.status_code == 400, r.text
        print("last-admin guard OK")

        # Logout.
        assert c.post("/api/auth/logout").status_code == 204
        assert c.get("/api/auth/me").status_code == 401
        print("logout OK")

    print("\nALL SMOKE CHECKS PASSED")


if __name__ == "__main__":
    main()
