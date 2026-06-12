import io
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.payment_application.service import (
    get_applications, create_application, update_actual_payment
)
from modules.payment_memo.service import get_memo_list
from modules.payment_application.exports import export_application_excel

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
    company_id = session["company_id"]
    month = request.args.get("month", type=int)
    year  = request.args.get("year", type=int)
    applications = get_applications(company_id, month=month, year=year)
    approved_memos = [m for m in get_memo_list(company_id, status="on_process")
                      if not any(a["memo_id"] == m["id"] for a in applications)]
    return render_template(
        "payment_application/index.html",
        applications=applications,
        approved_memos=approved_memos,
        active_page="payment_app",
        filter_month=month,
        filter_year=year,
        **_ctx()
    )


@bp.route("/create", methods=["POST"])
@jwt_html_required
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
@jwt_html_required
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


@bp.route("/export")
@jwt_html_required
def export_route():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    month = request.args.get("month", type=int)
    year  = request.args.get("year",  type=int)
    xls   = export_application_excel(company_id, month, year)
    fname = f"Payment_Application_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        io.BytesIO(xls),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=fname,
        as_attachment=True,
    )
