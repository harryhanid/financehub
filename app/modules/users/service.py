import bcrypt
from database import get_conn

VALID_ROLES = {"requester", "verificator", "releaser"}


def get_users() -> list:
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, username, role, is_active, must_change_pw, created_at, last_login FROM users ORDER BY created_at"
    ).fetchall()]
    conn.close()
    return rows


def add_user(username: str, password: str, role: str) -> dict:
    username = username.strip()
    if not username:
        return {"ok": False, "pesan": "Username wajib diisi."}
    if len(password) < 8:
        return {"ok": False, "pesan": "Password minimal 8 karakter."}
    if role not in VALID_ROLES:
        return {"ok": False, "pesan": f"Role tidak valid. Pilihan: {', '.join(VALID_ROLES)}"}
    conn     = get_conn()
    existing = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if existing:
        conn.close()
        return {"ok": False, "pesan": f"Username '{username}' sudah ada."}
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()
    conn.execute(
        "INSERT INTO users (username, password_hash, role, must_change_pw) VALUES (?,?,?,1)",
        (username, pw_hash, role)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"User '{username}' berhasil ditambahkan (role: {role})."}


def toggle_user_active(username: str, is_active: bool) -> dict:
    if username == "admin":
        return {"ok": False, "pesan": "User 'admin' tidak dapat dinonaktifkan."}
    conn = get_conn()
    conn.execute("UPDATE users SET is_active=? WHERE username=?", (int(is_active), username))
    conn.commit()
    conn.close()
    status = "diaktifkan" if is_active else "dinonaktifkan"
    return {"ok": True, "pesan": f"User '{username}' berhasil {status}."}


def change_user_role(username: str, new_role: str) -> dict:
    if username == "admin":
        return {"ok": False, "pesan": "Role user 'admin' tidak dapat diubah."}
    if new_role not in VALID_ROLES:
        return {"ok": False, "pesan": "Role tidak valid."}
    conn = get_conn()
    conn.execute("UPDATE users SET role=? WHERE username=?", (new_role, username))
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"Role '{username}' berhasil diubah ke '{new_role}'."}
