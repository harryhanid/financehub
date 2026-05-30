from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required, role_required
from modules.payment_memo.service import (
    get_draft_payments, create_memo, get_memo_list, get_memo_detail,
    update_memo_status, export_memo_pdf
)
import io

bp = Blueprint("payment_memo", __name__, url_prefix="/payment-memo")


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
    memos  = get_memo_list(session["company_id"])
    drafts = get_draft_payments(session["company_id"])
    return render_template(
        "payment_memo/index.html",
        memos=memos,
        drafts=drafts,
        active_page="payment_memo",
        **_ctx()
    )


@bp.route("/drafts")
@role_required("requester", "verificator", "releaser")
def list_drafts():
    rows = get_draft_payments(session.get("company_id"))
    return jsonify({"ok": True, "rows": rows})


@bp.route("/create", methods=["POST"])
@role_required("verificator")
def create():
    data         = request.get_json(force=True)
    company_id   = session.get("company_id")
    company_code = session.get("company_code", "")
    tanggal      = data.get("tanggal", "")
    notes        = data.get("notes", "")
    items        = data.get("items", [])
    claims       = get_jwt()
    username     = claims.get("username", "")
    if not items:
        return jsonify({"ok": False, "pesan": "Pilih minimal 1 payment."})
    result = create_memo(company_id, company_code, tanggal, notes, username, items)
    return jsonify(result)


@bp.route("/<int:memo_id>")
@role_required("requester", "verificator", "releaser")
def memo_detail_api(memo_id):
    memo = get_memo_detail(memo_id, session.get("company_id"))
    if not memo:
        return jsonify({"ok": False, "pesan": "Memo tidak ditemukan."}), 404
    return jsonify({"ok": True, "data": memo})


@bp.route("/<int:memo_id>/status", methods=["POST"])
@role_required("verificator", "releaser")
def update_status(memo_id):
    data       = request.get_json(force=True)
    new_status = data.get("status", "")
    claims     = get_jwt()
    username   = claims.get("username", "")
    if new_status == "paid" and claims.get("role") != "releaser":
        return jsonify({"ok": False, "pesan": "Hanya Releaser yang dapat mark as Paid."}), 403
    result = update_memo_status(memo_id, new_status, username)
    return jsonify(result)


@bp.route("/<int:memo_id>/export/pdf")
@role_required("verificator", "releaser")
def export_pdf(memo_id):
    company_id   = session.get("company_id")
    company_name = session.get("company_name", "")
    try:
        pdf_bytes = export_memo_pdf(memo_id, company_id, company_name)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            download_name=f"memo_{memo_id}.pdf",
            as_attachment=True
        )
    except ValueError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 404
