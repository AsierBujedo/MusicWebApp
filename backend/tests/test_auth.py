from __future__ import annotations


def test_me_requires_auth(client):
    client.cookies.clear()
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_login_logout_flow(client):
    client.cookies.clear()
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "admin"
    assert body["role"] == "ADMIN"
    assert body["displayName"]  # camelCase surfaced

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == body["id"]

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_bad_password_rejected(client):
    client.cookies.clear()
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_change_password(client):
    # Use a throwaway user so we never mutate the shared admin credentials.
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    client.post(
        "/api/admin/users",
        json={"username": "carol", "password": "password1", "displayName": "Carol", "role": "USER"},
    )
    client.post("/api/auth/logout")

    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "carol", "password": "password1"})
    # wrong current password rejected
    bad = client.post(
        "/api/auth/password",
        json={"currentPassword": "nope", "newPassword": "supersecret1"},
    )
    assert bad.status_code == 400
    # correct rotation
    ok = client.post(
        "/api/auth/password",
        json={"currentPassword": "password1", "newPassword": "supersecret1"},
    )
    assert ok.status_code == 204
    client.post("/api/auth/logout")

    # can log in with the new password
    client.cookies.clear()
    relog = client.post("/api/auth/login", json={"username": "carol", "password": "supersecret1"})
    assert relog.status_code == 200
    client.post("/api/auth/logout")
