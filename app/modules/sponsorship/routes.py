# modules/sponsorship/routes.py
from datetime import datetime
from functools import wraps
import io
from flask import Blueprint, render_template, request, jsonify, session, send_file, redirect, url_for
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.sponsorship.service import (
    list_perusahaan, get_lembaga_suggestions, create_transaksi, create_transaksi_bulk, get_transaksi, delete_transaksi,
    update_transaksi, list_transaksi, count_transaksi, get_available_years,
    get_dashboard_data, get_sponsorship_report, get_sponsorship_mr,
    create_perusahaan, update_perusahaan, delete_perusahaan, sync_transaksi_excel,
    normalise_bulan, MONTH_CHOICES,
)
from modules.sponsorship.exports import export_report_excel, export_mr_excel, format_tanggal_indo, format_terbilang, format_terbilang_pillar
import config

bp = Blueprint("sponsorship", __name__, url_prefix="/sponsorship")

PER_PAGE = 100
PER_PAGE_MAX = PER_PAGE * 4


def _resolve_page_size():
    from flask import request
    try:
        requested = int(request.args.get("page_size", PER_PAGE))
    except ValueError:
        return PER_PAGE
    if 1 <= requested <= PER_PAGE_MAX:
        return requested
    return PER_PAGE


def smt_company_required(f):
    """Sponsorship data is SMT-only. Guards HTML pages (via wrong_company flag,
    handled per-route below) AND API/mutating endpoints (via 403 here) — see
    the Bank Sahabat ETF finding (2026-07-14) that a guard on the index page
    alone does not stop direct hits to API/export URLs."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("company_code") != "SMT":
            return jsonify({"ok": False, "pesan": "Akses ditolak. Modul ini khusus company SMT."}), 403
        return f(*args, **kwargs)
    return decorated


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


def _wrong_company():
    return session.get("company_code") != "SMT"


def _parse_filters():
    filters = {}
    is_initial = len(request.args) == 0

    for key in ("cat1", "cat2", "cat4", "description", "keyword"):
        val = request.args.get(key)
        if val:
            filters[key] = val

    for key in ("cat", "cat3"):
        vals = [v for v in request.args.getlist(key) if v.strip()]
        if vals:
            filters[key] = vals

    tahun_vals = [y for y in request.args.getlist("tahun") if y.strip()]
    if tahun_vals:
        filters["tahun"] = tahun_vals
    elif is_initial:
        import datetime
        filters["tahun"] = [str(datetime.date.today().year)]

    return filters


def _parse_report_params():
    tahun_vals = request.args.getlist("tahun")
    tahun = [y for y in tahun_vals if y.strip()]
    if not tahun:
        years = get_available_years(_cid())
        tahun = [years[0]] if years else [str(datetime.now().year)]
    cat4 = (request.args.get("cat4") or "all").lower()
    if cat4 not in ("include", "exclude", "all", "bib_include", "outstanding"):
        cat4 = "all"
    bulan = normalise_bulan(request.args.getlist("bulan"))
    return tahun, cat4, bulan


def _parse_mr_params():
    tahun_vals = request.args.getlist("tahun")
    tahun = [y for y in tahun_vals if y.strip()]
    if not tahun:
        years = get_available_years(_cid())
        tahun = [years[0]] if years else [str(datetime.now().year)]
    return tahun


@bp.route("/")
@jwt_html_required
def index():
    years = get_available_years(_cid()) if not _wrong_company() else []
    return render_template("sponsorship/dashboard.html", active_page="sponsorship",
                            use_unified_header=True,
                            wrong_company=_wrong_company(), years=years,
                            cat_choices=config.SPONSORSHIP_CAT,
                            pillar_choices=config.SPONSORSHIP_PILLARS,
                            **_ctx())


@bp.route("/api/dashboard-data")
@jwt_html_required
@smt_company_required
def api_dashboard_data():
    filters = _parse_filters()
    cat4_mode = (request.args.get("cat4") or "all").lower()
    # Remove raw cat4 from filters to handle it via cat4_mode logic
    if "cat4" in filters: del filters["cat4"]
    data = get_dashboard_data(_cid(), filters, cat4_mode)
    return jsonify(data)


@bp.route("/api/report-data")
@jwt_html_required
@smt_company_required
def api_report_data():
    tahun, cat4, bulan = _parse_report_params()
    if cat4 == "outstanding":
        from modules.sponsorship.service import get_sponsorship_outstanding, list_proposals
        filters = {"tahun": tahun} if tahun else {}
        sections, grand_total = get_sponsorship_outstanding(_cid(), filters)
        prop_filters = {"status": "Open"}
        if tahun:
            prop_filters["tahun"] = tahun
        open_proposals = list_proposals(_cid(), prop_filters, limit=2000, offset=0)
        open_total = sum(float(p.get("total_amount") or 0) for p in open_proposals)
        months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
        for p in open_proposals:
            tgl_raw = p.get("tanggal") or ""
            tgl_display = tgl_raw
            if tgl_raw and len(tgl_raw) >= 7:
                try:
                    dt = datetime.strptime(tgl_raw[:10], "%Y-%m-%d")
                    tgl_display = f"{months[dt.month - 1]} {dt.year}"
                except Exception:
                    pass
            p["tanggal_approval"] = tgl_display
        return jsonify({
            "is_outstanding": True,
            "sections": sections,
            "grand_total": grand_total,
            "open_proposals": open_proposals,
            "open_proposals_total": open_total,
            "tahun": ", ".join(tahun) if tahun else ""
        })
    data = get_sponsorship_report(_cid(), tahun, cat4, bulan)
    return jsonify(data)


@bp.route("/report/export")
@jwt_html_required
@smt_company_required
def export_report_route():
    tahun, cat4, bulan = _parse_report_params()
    if cat4 == "outstanding":
        from modules.sponsorship.exports import export_outstanding_excel
        filters = {"tahun": tahun} if tahun else {}
        xls_bytes = export_outstanding_excel(_cid(), filters)
        filename = f"Sponsorship_Outstanding_{'-'.join(tahun) if tahun else 'ALL'}.xlsx"
    else:
        xls_bytes = export_report_excel(_cid(), tahun, cat4, bulan)
        month_part = f"_{'-'.join(bulan)}" if bulan else ""
        filename = f"Sponsorship_Report_{cat4}_{'-'.join(tahun)}{month_part}.xlsx"
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )


@bp.route("/input")
@jwt_html_required
def input_page():
    return render_template("sponsorship/input.html", active_page="sponsorship",
                            use_unified_header=True,
                            wrong_company=_wrong_company(),
                            cat_choices=config.SPONSORSHIP_CAT,
                            description_choices=config.SPONSORSHIP_DESCRIPTION,
                            cat4_choices=config.SPONSORSHIP_CAT4,
                            **_ctx())


@bp.route("/api/lookups")
@jwt_html_required
@smt_company_required
def api_lookups():
    return jsonify({"perusahaan": list_perusahaan(), "lembaga": get_lembaga_suggestions(_cid())})


@bp.route("/input/create", methods=["POST"])
@jwt_html_required
@smt_company_required
def input_create():
    payload = request.get_json(force=True)
    result = create_transaksi(_cid(), payload)
    return jsonify(result)


@bp.route("/input/create-bulk", methods=["POST"])
@jwt_html_required
@smt_company_required
def input_create_bulk():
    payload = request.get_json(force=True)
    result = create_transaksi_bulk(_cid(), payload)
    return jsonify(result)

@bp.route("/data")
@jwt_html_required
def data_page():
    filters = _parse_filters()
    from modules.sponsorship.service import list_perusahaan
    plist = list_perusahaan()
    cat1_choices = sorted(list(set(p["cat1"] for p in plist if p.get("cat1"))))
    cat2_choices = sorted(list(set(p["cat2"] for p in plist if p.get("cat2"))))
    total = count_transaksi(_cid(), filters) if not _wrong_company() else 0
    page_size = _resolve_page_size()
    page = request.args.get("page", 1, type=int) or 1
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    rows = list_transaksi(_cid(), filters, limit=page_size, offset=(page - 1) * page_size) if not _wrong_company() else []
    years = get_available_years(_cid()) if not _wrong_company() else []
    return render_template(
        "sponsorship/data.html", active_page="sponsorship", use_unified_header=True,
        wrong_company=_wrong_company(),
        rows=rows, page=page, page_size=page_size, total_pages=total_pages, total_count=total, years=years,
        filters=filters,
        cat_choices=config.SPONSORSHIP_CAT, description_choices=config.SPONSORSHIP_DESCRIPTION,
        pillar_choices=config.SPONSORSHIP_PILLARS, cat4_choices=config.SPONSORSHIP_CAT4,
        cat1_choices=cat1_choices, cat2_choices=cat2_choices,
        **_ctx()
    )


@bp.route("/outstanding")
@jwt_html_required
@smt_company_required
def outstanding_page():
    filters = _parse_filters()
    
    # We will pass filters directly to get_sponsorship_outstanding
    if not _wrong_company():
        from .service import get_sponsorship_outstanding, list_proposals
        sections, grand_total = get_sponsorship_outstanding(_cid(), filters)
        prop_filters = {"status": "Open"}
        if filters.get("tahun"):
            prop_filters["tahun"] = filters.get("tahun")
        open_proposals = list_proposals(_cid(), prop_filters, limit=2000, offset=0)
        open_proposals_total = sum(float(p.get("total_amount") or 0) for p in open_proposals)
        months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
        for p in open_proposals:
            tgl_raw = p.get("tanggal") or ""
            tgl_display = tgl_raw
            if tgl_raw and len(tgl_raw) >= 7:
                try:
                    dt = datetime.strptime(tgl_raw[:10], "%Y-%m-%d")
                    tgl_display = f"{months[dt.month - 1]} {dt.year}"
                except Exception:
                    pass
            p["tanggal_approval"] = tgl_display
        years = get_available_years(_cid())
    else:
        sections = []
        grand_total = 0.0
        open_proposals = []
        open_proposals_total = 0.0
        years = []

    return render_template(
        "sponsorship/outstanding.html", active_page="sponsorship", use_unified_header=True,
        wrong_company=_wrong_company(),
        sections=sections, grand_total=grand_total,
        open_proposals=open_proposals, open_proposals_total=open_proposals_total,
        years=years,
        filters=filters,
        cat_choices=config.SPONSORSHIP_CAT, description_choices=config.SPONSORSHIP_DESCRIPTION,
        pillar_choices=config.SPONSORSHIP_PILLARS, cat4_choices=config.SPONSORSHIP_CAT4,
        **_ctx()
    )


@bp.route("/data/<int:transaksi_id>")
@jwt_html_required
@smt_company_required
def data_get(transaksi_id):
    row = get_transaksi(transaksi_id, company_id=_cid())
    if not row:
        return jsonify({"ok": False, "pesan": "Transaksi tidak ditemukan."}), 404
    return jsonify({"ok": True, "transaksi": row})


@bp.route("/data/<int:transaksi_id>/update", methods=["POST"])
@jwt_html_required
@smt_company_required
def data_update(transaksi_id):
    payload = request.get_json(force=True)
    result = update_transaksi(transaksi_id, payload, company_id=_cid())
    return jsonify(result)


@bp.route("/vendor")
@jwt_html_required
def vendor_page():
    rows = list_perusahaan() if not _wrong_company() else []
    cat2_choices = sorted(set(r["cat2"] for r in rows if r.get("cat2")))
    return render_template("sponsorship/vendor.html", active_page="sponsorship",
                            use_unified_header=True,
                            wrong_company=_wrong_company(), rows=rows,
                            cat2_choices=cat2_choices,
                            pillar_choices=config.SPONSORSHIP_PILLARS,
                            **_ctx())


@bp.route("/vendor/create", methods=["POST"])
@jwt_html_required
@smt_company_required
def vendor_create():
    payload = request.get_json(force=True)
    result = create_perusahaan(payload.get("cat1"), payload.get("cat2"), payload.get("cat3"))
    return jsonify(result)


@bp.route("/vendor/<cat1>/update", methods=["POST"])
@jwt_html_required
@smt_company_required
def vendor_update(cat1):
    payload = request.get_json(force=True)
    result = update_perusahaan(cat1, payload.get("cat2"), payload.get("cat3"))
    return jsonify(result)


@bp.route("/vendor/<cat1>/delete", methods=["POST"])
@jwt_html_required
@smt_company_required
def vendor_delete(cat1):
    result = delete_perusahaan(cat1)
    return jsonify(result)


@bp.route("/report")
@jwt_html_required
def report_page():
    years = get_available_years(_cid()) if not _wrong_company() else []
    return render_template("sponsorship/report.html", active_page="sponsorship",
                            use_unified_header=True,
                            wrong_company=_wrong_company(), years=years, months=MONTH_CHOICES, **_ctx())

@bp.route("/data/export")
@jwt_html_required
@smt_company_required
def export_data_route():
    from modules.sponsorship.exports import export_data_excel
    filters = _parse_filters()
    xls_bytes = export_data_excel(_cid(), filters)
    import io
    from flask import send_file
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Sponsorship - MASTER.xlsx"
    )

@bp.route("/outstanding/export")
@jwt_html_required
@smt_company_required
def export_outstanding_route():
    from modules.sponsorship.exports import export_outstanding_excel
    filters = _parse_filters()
    xls_bytes = export_outstanding_excel(_cid(), filters)
    import io
    from flask import send_file
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Sponsorship_Outstanding.xlsx"
    )


@bp.route("/mr")
@jwt_html_required
def mr_page():
    tahun = _parse_mr_params() if not _wrong_company() else []
    years = get_available_years(_cid()) if not _wrong_company() else []
    rows = get_sponsorship_mr(_cid(), tahun) if not _wrong_company() else []
    return render_template(
        "sponsorship/mr.html", active_page="sponsorship", use_unified_header=True,
        wrong_company=_wrong_company(),
        rows=rows, years=years, tahun=tahun,
        **_ctx()
    )


@bp.route("/mr/export")
@jwt_html_required
@smt_company_required
def export_mr_route():
    tahun = _parse_mr_params()
    xls_bytes = export_mr_excel(_cid(), tahun)
    filename = f"Sponsorship_MR_{'-'.join(tahun)}.xlsx"
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )

@bp.route("/data/<int:id>/delete", methods=["POST"])
@jwt_html_required
def data_delete(id):
    result = delete_transaksi(id, _cid() if not _wrong_company() else None)
    return jsonify(result)

@bp.route("/data/sync", methods=["POST"])
@jwt_html_required
@smt_company_required
def data_sync_route():
    if "file" not in request.files:
        return jsonify({"ok": False, "pesan": "File tidak ditemukan."})
    file = request.files["file"]
    if not file.filename.endswith(".xlsx"):
        return jsonify({"ok": False, "pesan": "Format file harus .xlsx"})
        
    file_bytes = file.read()
    result = sync_transaksi_excel(_cid(), file_bytes)
    return jsonify(result)


# --- Proposal & Sponsorship Form Routes ---

from modules.sponsorship.service import (
    list_proposals, count_proposals, get_proposal,
    create_proposal, update_proposal, update_proposal_status, delete_proposal,
    import_proposals_excel, get_available_proposal_years
)
from modules.sponsorship.exports import (
    export_proposal_form_excel, export_proposals_bulk_zip,
    terbilang_id, format_terbilang, format_terbilang_pillar
)


@bp.route("/proposal")
@jwt_html_required
def proposal_page():
    if _wrong_company():
        return render_template(
            "sponsorship/proposal.html", active_page="sponsorship", active_tab="proposal",
            use_unified_header=True, wrong_company=True, rows=[], total_count=0,
            page=1, page_size=PER_PAGE, total_pages=1, years=[], filters={},
            **_ctx()
        )

    filters = {}
    for key in ("tahun", "status", "keyword"):
        val = request.args.get(key)
        if val:
            filters[key] = val

    total = count_proposals(_cid(), filters)
    page_size = _resolve_page_size()
    page = request.args.get("page", 1, type=int) or 1
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    
    rows = list_proposals(_cid(), filters, limit=page_size, offset=(page - 1) * page_size)
    from modules.sponsorship.exports import format_terbilang, format_terbilang_pillar
    for r in rows:
        tot = float(r.get("total_amount") or 0)
        r["terbilang_total"] = format_terbilang(tot)
        r["tanggal_indo"] = format_tanggal_indo(r.get("tanggal") or "")
        for pillar in ("app", "agri", "energy", "land", "finance"):
            amt = float(r.get(f"{pillar}_amount") or 0)
            r[f"terbilang_{pillar}"] = format_terbilang_pillar(amt)
    years = get_available_proposal_years(_cid())

    return render_template(
        "sponsorship/proposal.html", active_page="sponsorship", active_tab="proposal",
        use_unified_header=True, wrong_company=False,
        rows=rows, total_count=total, page=page, page_size=page_size,
        total_pages=total_pages, years=years, filters=filters,
        **_ctx()
    )


@bp.route("/proposal/create", methods=["POST"])
@jwt_html_required
@smt_company_required
def proposal_create_route():
    payload = request.get_json(force=True, silent=True) or request.form.to_dict()
    result = create_proposal(_cid(), payload)
    return jsonify(result)


@bp.route("/proposal/<int:proposal_id>/update", methods=["POST"])
@jwt_html_required
@smt_company_required
def proposal_update_route(proposal_id):
    payload = request.get_json(force=True, silent=True) or request.form.to_dict()
    result = update_proposal(_cid(), proposal_id, payload)
    return jsonify(result)


@bp.route("/proposal/<int:proposal_id>/status", methods=["POST"])
@jwt_html_required
@smt_company_required
def proposal_status_route(proposal_id):
    payload = request.get_json(force=True, silent=True) or request.form.to_dict()
    status = payload.get("status", "Open")
    approval_date = payload.get("approval_date", "")
    result = update_proposal_status(_cid(), proposal_id, status, approval_date)
    return jsonify(result)


@bp.route("/proposal/<int:proposal_id>/attachment", methods=["POST"])
@jwt_html_required
@smt_company_required
def proposal_upload_attachment_route(proposal_id):
    if "file" not in request.files:
        return jsonify({"ok": False, "pesan": "File tidak ditemukan."}), 400
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"ok": False, "pesan": "Nama file tidak valid."}), 400

    from utils.gdrive_service import create_gdrive_folder, upload_file_to_gdrive, delete_gdrive_file
    from modules.sponsorship.service import get_proposal, update_proposal_attachment

    p = get_proposal(_cid(), proposal_id)
    if not p:
        return jsonify({"ok": False, "pesan": "Proposal tidak ditemukan."}), 404

    try:
        old_fid = p.get("attachment_file_id")
        if old_fid:
            try:
                delete_gdrive_file(old_fid)
            except Exception:
                pass

        folder_id = create_gdrive_folder("Sponsorship Proposals")
        fid = upload_file_to_gdrive(file, file.filename, file.mimetype, parent_folder_id=folder_id)
        res = update_proposal_attachment(_cid(), proposal_id, fid, file.filename)
        res["file_id"] = fid
        res["filename"] = file.filename
        return jsonify(res)
    except Exception as e:
        return jsonify({"ok": False, "pesan": f"Gagal upload ke Google Drive: {str(e)}"}), 500


@bp.route("/proposal/<int:proposal_id>/attachment/delete", methods=["POST"])
@jwt_html_required
@smt_company_required
def proposal_delete_attachment_route(proposal_id):
    from modules.sponsorship.service import delete_proposal_attachment
    res = delete_proposal_attachment(_cid(), proposal_id)
    return jsonify(res)


@bp.route("/proposal/attachment/<file_id>")
@jwt_html_required
@smt_company_required
def proposal_view_attachment_route(file_id):
    from utils.gdrive_service import get_file_stream_from_gdrive, get_file_metadata_from_gdrive
    try:
        meta = get_file_metadata_from_gdrive(file_id)
        file_stream = get_file_stream_from_gdrive(file_id)
        return send_file(
            file_stream,
            as_attachment=False,
            mimetype=meta.get("mimeType", "application/octet-stream"),
            download_name=meta.get("name", "attachment")
        )
    except Exception as e:
        return f"Gagal memuat attachment dari Google Drive: {str(e)}", 500


@bp.route("/proposal/<int:proposal_id>/delete", methods=["POST"])
@jwt_html_required
@smt_company_required
def proposal_delete_route(proposal_id):
    result = delete_proposal(_cid(), proposal_id)
    return jsonify(result)


@bp.route("/proposal/import-excel", methods=["POST"])
@jwt_html_required
@smt_company_required
def proposal_import_excel_route():
    if "file" not in request.files:
        return jsonify({"ok": False, "pesan": "File excel tidak ditemukan."})
    file = request.files["file"]
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        return jsonify({"ok": False, "pesan": "Format file harus .xlsx"})

    file_bytes = io.BytesIO(file.read())
    result = import_proposals_excel(_cid(), file_bytes)
    return jsonify(result)


@bp.route("/proposal/export")
@jwt_html_required
@smt_company_required
def proposal_export_route():
    from modules.sponsorship.exports import export_proposals_master_excel
    filters = {}
    for key in ("tahun", "status", "keyword"):
        val = request.args.get(key)
        if val:
            filters[key] = val
    xls_bytes = export_proposals_master_excel(_cid(), filters)
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Proposal_Sponsorship_MASTER.xlsx"
    )


@bp.route("/proposal/sync", methods=["POST"])
@jwt_html_required
@smt_company_required
def proposal_sync_route():
    from modules.sponsorship.service import sync_proposals_excel
    if "file" not in request.files:
        return jsonify({"ok": False, "pesan": "File excel tidak ditemukan."})
    file = request.files["file"]
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        return jsonify({"ok": False, "pesan": "Format file harus .xlsx"})

    file_bytes = file.read()
    result = sync_proposals_excel(_cid(), file_bytes)
    return jsonify(result)


@bp.route("/form")
@bp.route("/form/<int:proposal_id>")
@jwt_html_required
def form_page(proposal_id=None):
    prop_id = proposal_id or request.args.get("proposal_id")
    if prop_id:
        return redirect(url_for("sponsorship.proposal_page", open_form=prop_id))
    return redirect(url_for("sponsorship.proposal_page"))


@bp.route("/proposal/<int:proposal_id>/form-data")
@jwt_html_required
@smt_company_required
def proposal_form_data(proposal_id):
    from modules.sponsorship.service import get_proposal
    from modules.sponsorship.exports import format_terbilang, format_terbilang_pillar
    p = get_proposal(_cid(), proposal_id)
    if not p:
        return jsonify({"ok": False, "pesan": "Proposal tidak ditemukan"}), 404
    tot = float(p.get("total_amount") or 0)
    p["terbilang_total"] = format_terbilang(tot)
    p["tanggal_indo"] = format_tanggal_indo(p.get("tanggal") or "")
    for pillar in ("app", "agri", "energy", "land", "finance"):
        amt = float(p.get(f"{pillar}_amount") or 0)
        p[f"terbilang_{pillar}"] = format_terbilang_pillar(amt)
    return jsonify({"ok": True, "proposal": p})


@bp.route("/form/<int:proposal_id>/export-excel")
@jwt_html_required
@smt_company_required
def form_export_excel_route(proposal_id):
    proposal = get_proposal(_cid(), proposal_id)
    if not proposal:
        return jsonify({"ok": False, "pesan": "Proposal tidak ditemukan."}), 404

    xls_bytes = export_proposal_form_excel(proposal)
    no_clean = (proposal.get("nomor_proposal") or f"PROP_{proposal_id}").replace("/", "_").replace("\\", "_")
    filename = f"Sponsorship_Form_{no_clean}.xlsx"

    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True
    )


@bp.route("/form/export-bulk")
@jwt_html_required
@smt_company_required
def form_export_bulk_route():
    filters = {}
    for key in ("tahun", "status", "keyword"):
        val = request.args.get(key)
        if val:
            filters[key] = val

    proposals = list_proposals(_cid(), filters, limit=1000, offset=0)
    if not proposals:
        return jsonify({"ok": False, "pesan": "Tidak ada data proposal untuk diekspor."}), 404

    zip_bytes = export_proposals_bulk_zip(proposals)
    filename = "Sponsorship_Forms_Bulk.zip"

    return send_file(
        io.BytesIO(zip_bytes),
        mimetype="application/zip",
        download_name=filename,
        as_attachment=True
    )


@bp.route("/api/proposals")
@jwt_html_required
@smt_company_required
def api_proposals_route():
    keyword = request.args.get("q", "")
    filters = {"keyword": keyword} if keyword else {}
    rows = list_proposals(_cid(), filters, limit=50, offset=0)
    return jsonify(rows)
