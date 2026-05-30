import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db
from modules.users.service import get_users, add_user, toggle_user_active, change_user_role

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)

def test_get_users_returns_admin():
    users = get_users()
    assert any(u["username"] == "admin" for u in users)

def test_add_user_success():
    result = add_user("staff01", "Pass@word1", "requester")
    assert result["ok"] is True

def test_add_user_duplicate_username():
    add_user("staff01", "Pass@word1", "requester")
    result = add_user("staff01", "Pass@word2", "verificator")
    assert result["ok"] is False
    assert "sudah ada" in result["pesan"]

def test_add_user_invalid_role():
    result = add_user("staff02", "Pass@word1", "superadmin")
    assert result["ok"] is False

def test_add_user_short_password():
    result = add_user("staff03", "short", "requester")
    assert result["ok"] is False
    assert "8" in result["pesan"]

def test_toggle_user_active():
    add_user("staff01", "Pass@word1", "requester")
    result = toggle_user_active("staff01", False)
    assert result["ok"] is True
    users  = get_users()
    staff  = next(u for u in users if u["username"] == "staff01")
    assert staff["is_active"] == 0

def test_change_user_role():
    add_user("staff01", "Pass@word1", "requester")
    result = change_user_role("staff01", "verificator")
    assert result["ok"] is True
    users  = get_users()
    staff  = next(u for u in users if u["username"] == "staff01")
    assert staff["role"] == "verificator"

def test_cannot_change_admin_role():
    result = change_user_role("admin", "requester")
    assert result["ok"] is False
