from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.payment_memo.service import (
    get_draft_payments, create_memo, get_memo_list, get_memo_detail,
    update_memo_status, export_memo_pdf,
    get_pam_list, get_coa_list, update_pam_gl_account,
    update_pam_status, update_pam_record,
    get_pam_detail, get_pam_payments, get_pam_payments_detail,
    update_pam_and_application,
    get_draft_payment_detail, update_draft_and_linked,
    delete_payment_beasiswa, cancel_pam_record,
    get_days_of_pam, get_days_of_pam_candidates, bulk_update_dates,
    set_memo_tanggal_bayar,
)
from modules.payment_memo.exports import (
    export_pam_pdf, export_pam_excel,
    export_pam_pdf_custom, export_pam_excel_custom,
)
import config, io

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
    company_id = session["company_id"]
    memos      = get_memo_list(company_id)
    drafts     = get_draft_payments(company_id)
    return render_template(
        "payment_memo/index.html",
        memos=memos,
        drafts=drafts,
        cat1_list=config.CAT1_BGT,
        cat2_list=config.CAT2_SEM,
        active_page="payment_memo",
        pam_approved_by_1=config.PAM_APPROVED_BY_1,
        pam_approved_by_2=config.PAM_APPROVED_BY_2,
        **_ctx()
    )


@bp.route("/drafts")
@jwt_html_required
def list_drafts():
    rows = get_draft_payments(session.get("company_id"))
    return jsonify({"ok": True, "rows": rows})


@bp.route("/create", methods=["POST"])
@jwt_html_required
def create():
    data         = request.get_json(force=True)
    company_id   = session.get("company_id")
    company_code = session.get("company_code", "")
    tanggal      = data.get("tanggal", "")
    notes        = data.get("notes", "")
    items        = data.get("items", [])
    claims       = get_jwt()
    username     = claims.get("username", "")
    if tanggal:
        try:
            from datetime import datetime as dt
            dt.strptime(tanggal, "%Y-%m-%d")
        except ValueError:
            return jsonify({"ok": False, "pesan": "Format tanggal tidak valid (YYYY-MM-DD)."}), 400
    if not items:
        return jsonify({"ok": False, "pesan": "Pilih minimal 1 payment."})
    result = create_memo(company_id, company_code, tanggal, notes, username, items)
    return jsonify(result)


@bp.route("/<int:memo_id>")
@jwt_html_required
def memo_detail_api(memo_id):
    memo = get_memo_detail(memo_id, session.get("company_id"))
    if not memo:
        return jsonify({"ok": False, "pesan": "Memo tidak ditemukan."}), 404
    return jsonify({"ok": True, "data": memo})


@bp.route("/<int:memo_id>/status", methods=["POST"])
@jwt_html_required
def update_status(memo_id):
    data       = request.get_json(force=True)
    new_status = data.get("status", "")
    claims     = get_jwt()
    username   = claims.get("username", "")
    if new_status == "paid" and claims.get("role") != "releaser":
        return jsonify({"ok": False, "pesan": "Hanya Releaser yang dapat mark as Paid."}), 403
    result = update_memo_status(memo_id, new_status, username, company_id=session.get("company_id", 0))
    return jsonify(result)


@bp.route("/<int:memo_id>/export/pdf")
@jwt_html_required
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


@bp.route("/coa")
@jwt_html_required
def list_coa():
    # COA is a global lookup — same chart of accounts across all companies
    return jsonify({"ok": True, "coa": get_coa_list()})


@bp.route("/pam")
@jwt_html_required
def list_pam():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    rows = get_pam_list(
        company_id,
        search=request.args.get("search", ""),
        bulan=request.args.get("bulan", ""),
        tahun=request.args.get("tahun", ""),
    )
    return jsonify({"ok": True, "rows": rows})


@bp.route("/pam/<int:pam_id>/status", methods=["POST"])
@jwt_html_required
def update_pam_status_route(pam_id):
    data       = request.get_json(force=True) or {}
    new_status = (data.get("status") or "").strip()
    if not new_status:
        return jsonify({"ok": False, "pesan": "Status wajib diisi."}), 400
    result = update_pam_status(pam_id, new_status, session.get("company_id", 0))
    return jsonify(result)


@bp.route("/pam/<int:pam_id>/detail")
@jwt_html_required
def get_pam_detail_route(pam_id):
    company_id = session.get("company_id", 0)
    detail = get_pam_detail(pam_id, company_id)
    if not detail:
        return jsonify({"ok": False, "pesan": "PAM record tidak ditemukan."}), 404
    detail["payments"] = get_pam_payments(detail["pam_no"], company_id)
    detail["payments_detail"] = get_pam_payments_detail(detail["pam_no"], company_id)
    return jsonify({"ok": True, "data": detail})


@bp.route("/pam/<int:pam_id>/edit", methods=["POST"])
@jwt_html_required
def update_pam_record_route(pam_id):
    data     = request.get_json(force=True) or {}
    pam_data = data.get("pam", {})
    app_data = data.get("app", {})
    result   = update_pam_and_application(pam_id, pam_data, app_data, session.get("company_id", 0))
    return jsonify(result)


@bp.route("/drafts/<int:payment_id>")
@jwt_html_required
def get_draft_detail_route(payment_id):
    detail = get_draft_payment_detail(payment_id, session.get("company_id", 0))
    if not detail:
        return jsonify({"ok": False, "pesan": "Draft payment tidak ditemukan."}), 404
    return jsonify({"ok": True, "data": detail})


@bp.route("/drafts/<int:payment_id>/edit", methods=["POST"])
@jwt_html_required
def update_draft_route(payment_id):
    data     = request.get_json(force=True) or {}
    pb_data  = data.get("payment", {})
    pam_data = data.get("pam", {})
    app_data = data.get("app", {})
    result   = update_draft_and_linked(payment_id, pb_data, pam_data, app_data,
                                       session.get("company_id", 0))
    return jsonify(result)


@bp.route("/drafts/<int:payment_id>/delete", methods=["POST"])
@jwt_html_required
def delete_draft_route(payment_id):
    result = delete_payment_beasiswa(payment_id, session.get("company_id", 0))
    return jsonify(result)


@bp.route("/pam/<int:pam_id>/export/pdf")
@jwt_html_required
def export_pam_pdf_route(pam_id):
    company_id    = session.get("company_id")
    approved_by_1 = request.args.get("approved_by_1", "").strip()
    approved_by_2 = request.args.get("approved_by_2", "").strip()
    try:
        pdf_bytes = export_pam_pdf(pam_id, company_id, approved_by_1, approved_by_2)
    except ValueError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 404
    pam      = get_pam_detail(pam_id, company_id)
    filename = f"{pam['pam_no']}.pdf" if pam else f"pam_{pam_id}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        download_name=filename,
        as_attachment=True,
    )


@bp.route("/pam/<int:pam_id>/export/excel")
@jwt_html_required
def export_pam_excel_route(pam_id):
    company_id    = session.get("company_id")
    approved_by_1 = request.args.get("approved_by_1", "").strip()
    approved_by_2 = request.args.get("approved_by_2", "").strip()
    try:
        xls_bytes = export_pam_excel(pam_id, company_id, approved_by_1, approved_by_2)
    except ValueError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 404
    pam      = get_pam_detail(pam_id, company_id)
    filename = f"{pam['pam_no']}.xlsx" if pam else f"pam_{pam_id}.xlsx"
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )


@bp.route("/days-of-pam/bulk-update", methods=["POST"])
@jwt_html_required
def days_of_pam_bulk_update():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    data  = request.get_json(force=True) or {}
    ids   = data.get("ids", [])
    dates = data.get("dates", {})
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        return jsonify({"ok": False, "pesan": "Format ids tidak valid."}), 400
    result = bulk_update_dates(ids, dates, company_id)
    return jsonify(result)


@bp.route("/days-of-pam/candidates")
@jwt_html_required
def days_of_pam_candidates_route():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    return jsonify({"ok": True, "candidates": get_days_of_pam_candidates(company_id)})


@bp.route("/days-of-pam/search")
@jwt_html_required
def days_of_pam_search_route():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    pam  = request.args.get("pam",  "").strip()
    nama = request.args.get("nama", "").strip().lower()
    if not pam and not nama:
        return jsonify({"ok": True, "rows": []})
    rows = get_days_of_pam(company_id)
    if pam:
        rows = [r for r in rows if pam.lower() in (r["pam_no"] or "").lower()]
    if nama:
        rows = [r for r in rows if nama in (r["nama"] or "").lower()]
    return jsonify({"ok": True, "rows": rows})


@bp.route("/pam/<int:pam_id>/cancel", methods=["POST"])
@jwt_html_required
def cancel_pam_route(pam_id):
    result = cancel_pam_record(pam_id, session.get("company_id", 0))
    return jsonify(result)


@bp.route("/pam/<int:pam_id>/gl-account", methods=["POST"])
@jwt_html_required
def update_gl_account(pam_id):
    data       = request.get_json(force=True) or {}
    gl_account = (data.get("gl_account") or "").strip()
    if not gl_account:
        return jsonify({"ok": False, "pesan": "GL Account wajib diisi."}), 400
    result = update_pam_gl_account(pam_id, gl_account, session.get("company_id", 0))
    return jsonify(result)


@bp.route("/pam/<int:pam_id>/export/pdf-custom", methods=["POST"])
@jwt_html_required
def export_pam_pdf_custom_route(pam_id):
    data       = request.get_json(force=True) or {}
    company_id = session.get("company_id", 0)
    if not get_pam_detail(pam_id, company_id):
        return jsonify({"ok": False, "pesan": "PAM record tidak ditemukan."}), 404
    pam_no     = (data.get("pam_no") or "").strip()
    data["company_id"] = company_id
    payments   = get_pam_payments(pam_no, company_id)
    pdf_bytes  = export_pam_pdf_custom(data, payments)
    fname      = f"{pam_no or f'pam_{pam_id}'}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        download_name=fname,
        as_attachment=True,
    )


@bp.route("/pam/<int:pam_id>/export/excel-custom", methods=["POST"])
@jwt_html_required
def export_pam_excel_custom_route(pam_id):
    data       = request.get_json(force=True) or {}
    company_id = session.get("company_id", 0)
    if not get_pam_detail(pam_id, company_id):
        return jsonify({"ok": False, "pesan": "PAM record tidak ditemukan."}), 404
    pam_no                = (data.get("pam_no") or "").strip()
    data["company_id"]    = company_id
    payments              = get_pam_payments(pam_no, company_id)
    xls_bytes             = export_pam_excel_custom(data, payments)
    fname      = f"{pam_no or f'pam_{pam_id}'}.xlsx"
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=fname,
        as_attachment=True,
    )


@bp.route("/<int:memo_id>/tanggal-bayar", methods=["POST"])
@jwt_html_required
def memo_tanggal_bayar(memo_id):
    company_id = session.get("company_id")
    data = request.get_json(force=True) or {}
    return jsonify(set_memo_tanggal_bayar(
        memo_id,
        data.get("tanggal_bayar", ""),
        company_id,
    ))
