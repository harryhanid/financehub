# Database test: Postgres lokal lewat fixture clean_db di conftest.py (autouse).
from modules.users.service import get_users, add_user, toggle_user_active, change_user_role

def test_get_users_returns_admin():
    users = get_users()
    assert any(u["username"] == "admin" for u in users)

def test_add_user_success():
    result = add_user("staff01", "Pass@word1", "Fin")
    assert result["ok"] is True

def test_add_user_duplicate_username():
    add_user("staff01", "Pass@word1", "Fin")
    result = add_user("staff01", "Pass@word2", "FC")
    assert result["ok"] is False
    assert "sudah ada" in result["pesan"]

def test_add_user_invalid_role():
    result = add_user("staff02", "Pass@word1", "superadmin")
    assert result["ok"] is False

def test_add_user_short_password():
    result = add_user("staff03", "short", "Fin")
    assert result["ok"] is False
    assert "8" in result["pesan"]

def test_toggle_user_active():
    add_user("staff01", "Pass@word1", "Fin")
    result = toggle_user_active("staff01", False)
    assert result["ok"] is True
    users  = get_users()
    staff  = next(u for u in users if u["username"] == "staff01")
    assert staff["is_active"] == 0

def test_change_user_role():
    add_user("staff01", "Pass@word1", "Fin")
    result = change_user_role("staff01", "FC")
    assert result["ok"] is True
    users  = get_users()
    staff  = next(u for u in users if u["username"] == "staff01")
    assert staff["role"] == "FC"

def test_cannot_change_admin_role():
    result = change_user_role("admin", "Fin")
    assert result["ok"] is False


def test_get_users_null_created_at_first():
    """R29: SQLite mengurutkan NULL lebih dulu pada ASC."""
    from database import get_conn
    add_user("staff_null", "Pass@word1", "Fin")
    conn = get_conn()
    conn.execute("UPDATE users SET created_at=NULL WHERE username=?", ("staff_null",))
    conn.close()
    assert get_users()[0]["username"] == "staff_null"
