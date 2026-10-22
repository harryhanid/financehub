# auth/routes.py
import hashlib
from datetime import datetime, timedelta

import bcrypt
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import (
    create_access_token, create_refresh_token, get_jwt,
    get_jwt_identity, jwt_required,
    set_access_cookies, set_refresh_cookies, unset_jwt_cookies,
)

import config
from database import get_conn

bp = Blueprint("auth", __name__)


def _extract_refresh_token() -> str:
    """Find the raw refresh JWT string wherever the client sent it.

    Login always issues the refresh token via cookie (JWT_TOKEN_LOCATION
    includes "cookies"), so logout/refresh must check there too — checking
    only an optional request-body field let a revoked/logged-out refresh
    cookie keep minting new access tokens for up to JWT_REFRESH_DAYS.
    """
    data = request.get_json(silent=True) or {}
    token = data.get("refresh_token", "")
    if token:
        return token
    cookie_name = current_app.config.get("JWT_REFRESH_COOKIE_NAME", "refresh_token_cookie")
    token = request.cookies.get(cookie_name, "")
    if token:
        return token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return ""


@bp.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"ok": False, "pesan": "Username dan password wajib diisi."})

    conn = get_conn()
    row  = conn.execute(
        "SELECT id, password_hash, role, is_active, must_change_pw "
        "FROM users WHERE username = ?", (username,)
    ).fetchone()

    if row is None or not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        conn.close()
        return jsonify({"ok": False, "pesan": "Username atau password salah."})

    if not row["is_active"]:
        conn.close()
        return jsonify({"ok": False, "pesan": "Akun tidak aktif. Hubungi admin."})

    last_login = datetime.now().isoformat()

    additional    = {"username": username, "role": row["role"]}
    access_token  = create_access_token(identity=str(row["id"]), additional_claims=additional)
    refresh_token = create_refresh_token(identity=str(row["id"]), additional_claims=additional)

    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    expires_at = (datetime.now() + timedelta(days=config.JWT_REFRESH_DAYS)).isoformat()
    # Postgres: dua tulisan dalam satu batch (satu transaksi), supaya last_login tidak tercatat
    # tanpa refresh token (atau sebaliknya) kalau salah satunya gagal.
    conn.batch([
        ("UPDATE users SET last_login = ? WHERE id = ?", (last_login, row["id"])),
        ("INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
         (row["id"], token_hash, expires_at)),
    ])
    conn.commit()
    conn.close()

    resp = jsonify({
        "ok": True,
        "must_change_pw": bool(row["must_change_pw"]),
        "role": row["role"],
        "access_token": access_token,
    })
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp


@bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    refresh_token = _extract_refresh_token()
    if refresh_token:
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        conn = get_conn()
        conn.execute(
            "UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?", (token_hash,)
        )
        conn.commit()
        conn.close()
    resp = jsonify({"ok": True})
    unset_jwt_cookies(resp)
    return resp


@bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    refresh_token = _extract_refresh_token()
    if refresh_token:
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        conn       = get_conn()
        row        = conn.execute(
            "SELECT id, revoked FROM refresh_tokens WHERE token_hash = ?", (token_hash,)
        ).fetchone()
        conn.close()
        if row is None or row["revoked"]:
            return jsonify({"ok": False, "pesan": "Refresh token tidak valid."}), 401

    claims       = get_jwt()
    access_token = create_access_token(
        identity=get_jwt_identity(),
        additional_claims={"username": claims["username"], "role": claims["role"]},
    )
    resp = jsonify({"ok": True})
    set_access_cookies(resp, access_token)
    return resp


@bp.route("/change-password", methods=["GET"])
def change_password_page():
    return render_template("change_password.html")


@bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = int(get_jwt_identity())
    data    = request.get_json(force=True) or {}
    old_pw  = data.get("old_password", "")
    new_pw  = data.get("new_password", "")

    if len(new_pw) < 8:
        return jsonify({"ok": False, "pesan": "Password baru minimal 8 karakter."})

    conn = get_conn()
    row  = conn.execute(
        "SELECT password_hash FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if row is None:
        conn.close()
        return jsonify({"ok": False, "pesan": "Akun tidak ditemukan. Silakan login ulang."}), 401

    if not bcrypt.checkpw(old_pw.encode(), row["password_hash"].encode()):
        conn.close()
        return jsonify({"ok": False, "pesan": "Password lama salah."})

    if bcrypt.checkpw(new_pw.encode(), row["password_hash"].encode()):
        conn.close()
        return jsonify({"ok": False, "pesan": "Password baru tidak boleh sama dengan password lama."})

    new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt(12)).decode()
    conn.execute(
        "UPDATE users SET password_hash = ?, must_change_pw = 0 WHERE id = ?",
        (new_hash, user_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "pesan": "Password berhasil diubah."})
