# tests/test_auth.py

def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})

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
