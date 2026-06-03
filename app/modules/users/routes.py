from flask import Blueprint, render_template, request, jsonify, session
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.users.service import get_users, add_user, toggle_user_active, change_user_role

bp = Blueprint("users", __name__, url_prefix="/users")


def _ctx():
    try:
        claims = get_jwt()
        return {
            "current_user": claims.get("username", ""),
            "current_role": claims.get("role", ""),
            "company_id":   session.get("company_id"),
            "company_code": session.get("company_code"),
            "company_name": session.get("company_name"),
        }
    except Exception:
        return {}


@bp.route("/")
@jwt_html_required
def index():
    return render_template("users/index.html", users=get_users(),
                           active_page="users", **_ctx())


@bp.route("/add", methods=["POST"])
@jwt_html_required
def add():
    data   = request.get_json(force=True)
    result = add_user(data.get("username", ""), data.get("password", ""), data.get("role", ""))
    return jsonify(result)


@bp.route("/<username>/toggle", methods=["POST"])
@jwt_html_required
def toggle(username):
    data = request.get_json(force=True)
    if data is None:
        return jsonify({"ok": False, "pesan": "Request body tidak valid."}), 400
    raw = data.get("is_active")
    if not isinstance(raw, bool):
        return jsonify({"ok": False, "pesan": "is_active harus boolean."}), 400
    is_active = raw
    result    = toggle_user_active(username, is_active)
    return jsonify(result)


@bp.route("/<username>/role", methods=["POST"])
@jwt_html_required
def change_role(username):
    data   = request.get_json(force=True)
    result = change_user_role(username, data.get("role", ""))
    return jsonify(result)
