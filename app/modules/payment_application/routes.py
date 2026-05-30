from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required, role_required
from modules.payment_application.service import (
    get_applications, create_application, update_actual_payment
)
from modules.payment_memo.service import get_memo_list

bp = Blueprint("payment_application", __name__, url_prefix="/payment-application")


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
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))
    company_id   = session["company_id"]
    applications = get_applications(company_id)
    approved_memos = [m for m in get_memo_list(company_id, status="approved")
                      if not any(a["memo_id"] == m["id"] for a in applications)]
    return render_template(
        "payment_application/index.html",
        applications=applications,
        approved_memos=approved_memos,
        active_page="payment_app",
        **_ctx()
    )


@bp.route("/create", methods=["POST"])
@role_required("releaser")
def create():
    data       = request.get_json(force=True)
    company_id = session.get("company_id")
    result = create_application(
        company_id,
        int(data.get("memo_id", 0)),
        data.get("submitted_at", ""),
        data.get("target_payment_date", ""),
        data.get("notes", ""),
    )
    return jsonify(result)


@bp.route("/<int:app_id>/update-payment", methods=["POST"])
@role_required("releaser")
def update_payment(app_id):
    data        = request.get_json(force=True)
    actual_date = data.get("actual_payment_date", "")
    if not actual_date:
        return jsonify({"ok": False, "pesan": "Tanggal aktual wajib diisi."})
    try:
        from datetime import datetime as dt
        dt.strptime(actual_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"ok": False, "pesan": "Format tanggal tidak valid (YYYY-MM-DD)."}), 400
    result = update_actual_payment(app_id, actual_date, company_id=session.get("company_id", 0))
    return jsonify(result)
