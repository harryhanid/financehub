# tests/test_auth.py
import re


def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _cookie_value(resp, name):
    for raw in resp.headers.getlist("Set-Cookie"):
        m = re.match(rf"{name}=([^;]+)", raw)
        if m:
            return m.group(1)
    return None

def test_login_success(client):
    resp = login(client)
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["ok"] is True
    assert data["must_change_pw"] is True
    assert data["role"] == "releaser"

def test_login_wrong_password(client):
    resp = login(client, password="wrong")
    data = resp.get_json()
    assert data["ok"] is False
    assert "salah" in data["pesan"].lower()

def test_login_unknown_user(client):
    resp = login(client, username="ghost")
    data = resp.get_json()
    assert data["ok"] is False

def test_change_password_success(client):
    login(client)
    resp = client.post("/auth/change-password", json={
        "old_password": "Admin@123",
        "new_password": "NewPass@456"
    })
    data = resp.get_json()
    assert data["ok"] is True

def test_change_password_too_short(client):
    login(client)
    resp = client.post("/auth/change-password", json={
        "old_password": "Admin@123",
        "new_password": "short"
    })
    data = resp.get_json()
    assert data["ok"] is False
    assert "8 karakter" in data["pesan"]

def test_change_password_same_as_old(client):
    login(client)
    resp = client.post("/auth/change-password", json={
        "old_password": "Admin@123",
        "new_password": "Admin@123"
    })
    data = resp.get_json()
    assert data["ok"] is False

def test_logout(client):
    login(client)
    resp = client.post("/auth/logout", json={})
    data = resp.get_json()
    assert data["ok"] is True


def test_logout_revokes_cookie_refresh_token_even_without_body(client):
    """Real frontend usage: logout is called with an empty body ({}) because
    the refresh cookie is httponly and JS can never read it to echo it back.
    The server must revoke whatever refresh token is sitting in the cookie,
    not only one explicitly passed in the request body."""
    login_resp = login(client)
    raw_refresh = _cookie_value(login_resp, "fh_refresh")
    assert raw_refresh

    logout_resp = client.post("/auth/logout", json={})
    assert logout_resp.get_json()["ok"] is True

    # Replay the captured (pre-logout) refresh token directly — simulates
    # someone still holding onto it after the session claims to be over.
    replay = client.post("/auth/refresh", json={"refresh_token": raw_refresh},
                          headers={"Authorization": f"Bearer {raw_refresh}"})
    assert replay.status_code == 401


def test_change_password_when_user_deleted_mid_session(client, app):
    """A valid access token can outlive the user row (deleted by an admin
    while the session's JWT hasn't expired yet). change_password must
    respond gracefully instead of crashing on row["password_hash"]
    with row=None."""
    login(client)
    from database import get_conn
    with app.app_context():
        conn = get_conn()
        conn.execute("DELETE FROM refresh_tokens WHERE user_id = (SELECT id FROM users WHERE username='admin')")
        conn.execute("DELETE FROM users WHERE username = 'admin'")
        conn.commit()
        conn.close()

    resp = client.post("/auth/change-password", json={
        "old_password": "Admin@123",
        "new_password": "NewPass@456",
    })
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["ok"] is False


def test_refresh_rejects_revoked_token_from_cookie_alone(client):
    """Even when the client sends no refresh_token in the body at all (the
    normal browser flow — the cookie itself carries it), a revoked refresh
    token must be rejected, not silently accepted."""
    login_resp = login(client)
    raw_refresh = _cookie_value(login_resp, "fh_refresh")
    client.post("/auth/logout", json={})

    # Fresh client session with only the captured (now-revoked) token set
    # as the auth cookie — mirrors the real cookie-only refresh flow.
    client.set_cookie("fh_refresh", raw_refresh)
    resp = client.post("/auth/refresh", json={})
    assert resp.status_code == 401


def test_login_atomic_on_failure(client, monkeypatch):
    """Task 9 (atomic-flows.md): UPDATE users.last_login + INSERT refresh_tokens dalam satu batch.
    Paksa INSERT refresh_tokens gagal (token_hash NULL -> NOT NULL): last_login tidak boleh berubah
    dan tidak ada refresh token yang tersimpan."""
    import auth.routes as auth_routes
    from database import get_conn

    conn = get_conn()
    before_login = conn.execute("SELECT last_login FROM users WHERE username='admin'").fetchone()[0]
    before_tokens = conn.execute("SELECT COUNT(*) FROM refresh_tokens").fetchone()[0]
    conn.close()

    class _NullHash:
        def hexdigest(self):
            return None

    class _FakeHashlib:
        @staticmethod
        def sha256(_data):
            return _NullHash()

    monkeypatch.setattr(auth_routes, "hashlib", _FakeHashlib)
    try:
        resp = client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
        assert resp.status_code >= 500
    except Exception:
        pass  # TESTING: exception bisa diteruskan ke test client

    conn = get_conn()
    assert conn.execute("SELECT last_login FROM users WHERE username='admin'").fetchone()[0] == before_login
    assert conn.execute("SELECT COUNT(*) FROM refresh_tokens").fetchone()[0] == before_tokens
    conn.close()
