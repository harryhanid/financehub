# auth/middleware.py
from functools import wraps
from flask import jsonify, redirect, url_for
from flask_jwt_extended import verify_jwt_in_request, get_jwt

def jwt_html_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated


def json_required(f):
    """Like jwt_html_required, but for AJAX/JSON endpoints: on an expired or
    missing token, returns a 401 JSON body instead of redirecting to the
    login *page*. A redirect response still carries a 200 once fetch()
    follows it, so callers using apiFetch()'s `resp.status === 401` refresh
    check never see the failure — they get the login page's HTML back and
    JSON.parse() blows up on it instead. No role check, same access scope
    as jwt_html_required (any authenticated user)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({"ok": False, "pesan": "Token tidak valid atau expired."}), 401
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                return jsonify({"ok": False, "pesan": "Token tidak valid atau expired."}), 401
            claims = get_jwt()
            if claims.get("role") != "admin" and claims.get("role") not in roles:
                return jsonify({"ok": False, "pesan": "Akses ditolak."}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def html_role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                return redirect(url_for("auth.login_page"))
            claims = get_jwt()
            if claims.get("role") != "admin" and claims.get("role") not in roles:
                return redirect(url_for("dashboard.index"))
            return f(*args, **kwargs)
        return decorated
    return decorator

def api_role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                verify_jwt_in_request(locations=["headers"])
            except Exception:
                return jsonify({"ok": False, "pesan": "Token tidak valid."}), 401
            claims = get_jwt()
            if claims.get("role") != "admin" and claims.get("role") not in roles:
                return jsonify({"ok": False, "pesan": "Akses ditolak."}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
