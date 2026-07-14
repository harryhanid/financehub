from flask import Blueprint, render_template, session
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required

bp = Blueprint("bank", __name__, url_prefix="/bank")


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


def _cid():
    return session.get("company_id")


@bp.route("/")
@jwt_html_required
def index():
    return render_template(
        "bank/index.html",
        active_page="bank",
        **_ctx(),
    )
