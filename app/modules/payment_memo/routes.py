from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.beasiswa.service import get_siswa_list, get_vendors
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
    get_fiori_list, bulk_update_fiori_dates,
    update_fiori_status, cancel_fiori_record,
    get_fiori_detail, update_fiori_record,
    get_sml_list, bulk_update_sml_dates,
    update_sml_status, cancel_sml_record,
    get_open_etf_pa_for_pam, create_pam_from_etf_pa, set_pam_tanggal_bayar_agri,
    get_next_pam_no, save_pa_payment, check_pam_no_exists,
)
from modules.payment_memo.exports import (
    export_pam_pdf, export_pam_excel,
    export_pam_pdf_custom, export_pam_excel_custom,
    export_open_pam_excel, export_pam_tab_excel, export_fiori_excel,
    export_sml_excel,
)
from datetime import datetime
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
        cat1_bgt=config.CAT1_BGT,
        cat2_sem=config.CAT2_SEM,
        active_page="payment_memo",
        pam_approved_by_1=config.PAM_APPROVED_BY_1,
        pam_approved_by_2=config.PAM_APPROVED_BY_2,
        siswa_list=get_siswa_list(company_id),
        vendor_list=get_vendors(),
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
            datetime.strptime(tanggal, "%Y-%m-%d")
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
    if new_status == "complete" and claims.get("role") != "releaser":
        return jsonify({"ok": False, "pesan": "Hanya Releaser yang dapat mark as Complete."}), 403
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
        source=request.args.get("source", ""),
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
    pam      = request.args.get("pam",      "").strip() or None
    nama     = request.args.get("nama",     "").strip() or None
    source   = request.args.get("source",   "AGRI").strip().upper()
    paid_only = request.args.get("paid_only", "1") == "1"
    try:
        limit  = int(request.args.get("limit",  100))
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        limit, offset = 100, 0
    result = get_days_of_pam(
        company_id,
        source=source,
        paid_only=paid_only,
        pam=pam,
        nama=nama,
        limit=limit,
        offset=offset,
    )
    return jsonify({"ok": True, "rows": result["rows"], "total": result["total"],
                    "limit": limit, "offset": offset})


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


@bp.route("/export/open-pam")
@jwt_html_required
def export_open_pam_route():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    xls = export_open_pam_excel(company_id)
    fname = f"Open_PAM_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        io.BytesIO(xls),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=fname,
        as_attachment=True,
    )


@bp.route("/export/pam")
@jwt_html_required
def export_pam_tab_route():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    search = request.args.get("search", "").strip()
    bulan  = request.args.get("bulan",  "").strip()
    tahun  = request.args.get("tahun",  "").strip()
    source = request.args.get("source", "").strip()
    xls   = export_pam_tab_excel(company_id, search, bulan, tahun, source)
    fname = f"PAM_AGRI_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        io.BytesIO(xls),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=fname,
        as_attachment=True,
    )


@bp.route("/export/fiori")
@jwt_html_required
def export_fiori_route():
    search = request.args.get("search", "").strip()
    bulan  = request.args.get("bulan",  "").strip()
    tahun  = request.args.get("tahun",  "").strip()
    xls   = export_fiori_excel(search, bulan, tahun)
    fname = f"PAM_APP_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        io.BytesIO(xls),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=fname,
        as_attachment=True,
    )


@bp.route("/export/sml")
@jwt_html_required
def export_sml_route():
    search = request.args.get("search", "").strip()
    bulan  = request.args.get("bulan",  "").strip()
    tahun  = request.args.get("tahun",  "").strip()
    xls   = export_sml_excel(search, bulan, tahun)
    fname = f"PAM_SML_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        io.BytesIO(xls),
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


@bp.route("/fiori")
@jwt_html_required
def fiori_list():
    search = request.args.get("search", "").strip()
    bulan  = request.args.get("bulan",  "").strip()
    tahun  = request.args.get("tahun",  "").strip()
    rows   = get_fiori_list(search, bulan, tahun)
    return jsonify({"ok": True, "rows": rows})


@bp.route("/fiori/bulk-update", methods=["POST"])
@jwt_html_required
def fiori_bulk_update():
    data  = request.get_json(force=True) or {}
    ids   = data.get("ids", [])
    dates = data.get("dates", {})
    result = bulk_update_fiori_dates(ids, dates)
    return jsonify(result)


@bp.route("/fiori/<int:record_id>/status", methods=["POST"])
@jwt_html_required
def fiori_status(record_id):
    data = request.get_json(force=True) or {}
    return jsonify(update_fiori_status(record_id, data.get("status", "")))


@bp.route("/fiori/<int:record_id>/cancel", methods=["POST"])
@jwt_html_required
def fiori_cancel(record_id):
    return jsonify(cancel_fiori_record(record_id))


@bp.route("/sml")
@jwt_html_required
def sml_list_route():
    search = request.args.get("search", "").strip()
    bulan  = request.args.get("bulan",  "").strip()
    tahun  = request.args.get("tahun",  "").strip()
    rows   = get_sml_list(search, bulan, tahun)
    return jsonify({"ok": True, "rows": rows})


@bp.route("/sml/bulk-update", methods=["POST"])
@jwt_html_required
def sml_bulk_update():
    data  = request.get_json(force=True) or {}
    return jsonify(bulk_update_sml_dates(data.get("ids", []), data.get("dates", {})))


@bp.route("/sml/<int:record_id>/status", methods=["POST"])
@jwt_html_required
def sml_status(record_id):
    data = request.get_json(force=True) or {}
    return jsonify(update_sml_status(record_id, data.get("status", "")))


@bp.route("/sml/<int:record_id>/cancel", methods=["POST"])
@jwt_html_required
def sml_cancel(record_id):
    return jsonify(cancel_sml_record(record_id))


@bp.route("/fiori/<int:record_id>/detail")
@jwt_html_required
def fiori_detail(record_id):
    data = get_fiori_detail(record_id)
    if not data:
        return jsonify({"ok": False, "pesan": "Record tidak ditemukan."}), 404
    return jsonify({"ok": True, "data": data})


@bp.route("/fiori/<int:record_id>/edit", methods=["POST"])
@jwt_html_required
def fiori_edit(record_id):
    data = request.get_json(force=True) or {}
    return jsonify(update_fiori_record(record_id, data))


# ── AGRI ETF-PA → PAM workflow endpoints ────────────────────────────────────

@bp.route("/agri-pa-open")
@jwt_html_required
def agri_pa_open():
    """Return etf_pa with status='open' untuk dipilih di Input AGRI."""
    company_id = session.get("company_id")
    return jsonify({"ok": True, "rows": get_open_etf_pa_for_pam(company_id)})


@bp.route("/create-agri-pam", methods=["POST"])
@jwt_html_required
def create_agri_pam():
    """Buat PAM dari etf_pa yang dipilih → on_process + nomor_pam."""
    company_id   = session.get("company_id")
    company_code = session.get("company_code", "ETF")
    data         = request.get_json(force=True) or {}
    pam_date     = data.get("pam_date", "")
    pa_ids       = data.get("pa_ids", [])
    keterangan   = data.get("keterangan", "")
    return jsonify(create_pam_from_etf_pa(company_id, company_code, pam_date, pa_ids, keterangan))


@bp.route("/pam/<int:pam_id>/set-paid-agri", methods=["POST"])
@jwt_html_required
def set_paid_agri(pam_id):
    """Set tanggal_bayar di PAM AGRI → cascade complete ke etf_pa."""
    company_id   = session.get("company_id")
    data         = request.get_json(force=True) or {}
    tanggal_bayar = data.get("tanggal_bayar", "")
    return jsonify(set_pam_tanggal_bayar_agri(pam_id, tanggal_bayar, company_id))


@bp.route("/pam/check")
@jwt_html_required
def check_pam_no_route():
    pam_no = (request.args.get("pam_no") or "").strip()
    if not pam_no:
        return jsonify({"ok": True, "exists": False})
    return jsonify(check_pam_no_exists(session.get("company_id", 0), pam_no))


@bp.route("/ipay/next-pam-no")
@jwt_html_required
def ipay_next_pam_no():
    tab      = request.args.get("tab", "agri").lower()
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    company_id   = session.get("company_id", 0)
    company_code = session.get("company_code", "ETF")
    pam_no = get_next_pam_no(company_id, company_code, tab, date_str)
    return jsonify({"ok": True, "pam_no": pam_no})


@bp.route("/ipay/save-pa", methods=["POST"])
@jwt_html_required
def ipay_save_pa():
    data         = request.get_json(force=True) or {}
    company_id   = session.get("company_id", 0)
    company_code = session.get("company_code", "ETF")
    result = save_pa_payment(company_id, company_code, data)
    return jsonify(result)
