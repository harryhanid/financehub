"""Access-control tests for /users/* mutation endpoints.

Regression guard for the privilege-escalation bug where any authenticated
user (e.g. a requester) could create users or change roles because the
routes were protected only by jwt_html_required with no admin check.
"""
from modules.users.service import add_user


def _login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _login_as_requester(client, username="req01"):
    add_user(username, "Pass@word1", "Fin")
    return _login(client, username, "Pass@word1")


# ── admin (seeded 'admin' account) is allowed ──────────────────────────────

def test_admin_can_add_user(client):
    _login(client)  # seeded admin
    resp = client.post("/users/add", json={
        "username": "staff99", "password": "Pass@word1", "role": "Fin"
    })
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


def test_admin_can_change_role(client):
    _login(client)
    add_user("staff01", "Pass@word1", "Fin")
    resp = client.post("/users/staff01/role", json={"role": "FC"})
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


# ── non-admin is forbidden ─────────────────────────────────────────────────

def test_requester_cannot_add_user(client):
    _login_as_requester(client)
    resp = client.post("/users/add", json={
        "username": "hacker", "password": "Pass@word1", "role": "Admin"
    })
    assert resp.status_code == 403


def test_requester_cannot_change_own_role(client):
    _login_as_requester(client, "req02")
    resp = client.post("/users/req02/role", json={"role": "Admin"})
    assert resp.status_code == 403


def test_requester_cannot_toggle_user(client):
    _login_as_requester(client, "req03")
    add_user("victim", "Pass@word1", "FC")
    resp = client.post("/users/victim/toggle", json={"is_active": False})
    assert resp.status_code == 403


def test_unauthenticated_cannot_add_user(client):
    resp = client.post("/users/add", json={
        "username": "x", "password": "Pass@word1", "role": "Fin"
    })
    assert resp.status_code in (401, 403)
