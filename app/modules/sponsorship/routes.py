# modules/sponsorship/routes.py
from datetime import datetime
from functools import wraps
import io
from flask import Blueprint, render_template, request, jsonify, session, send_file
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.sponsorship.service import (
    list_perusahaan, get_lembaga_suggestions, create_transaksi, get_transaksi,
    update_transaksi, list_transaksi, count_transaksi, get_available_years,
    get_dashboard_data, get_sponsorship_report, get_sponsorship_mr,
    create_perusahaan, update_perusahaan, delete_perusahaan,
)
from modules.sponsorship.exports import export_report_excel, export_mr_excel
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

    for key in ("cat1", "cat2", "cat4", "description", "status"):
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
    if cat4 not in ("include", "exclude", "all", "bib_include"):
        cat4 = "all"
    return tahun, cat4


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
    tahun, cat4 = _parse_report_params()
    data = get_sponsorship_report(_cid(), tahun, cat4)
    return jsonify(data)


@bp.route("/report/export")
@jwt_html_required
@smt_company_required
def export_report_route():
    tahun, cat4 = _parse_report_params()
    xls_bytes = export_report_excel(_cid(), tahun, cat4)
    filename = f"Sponsorship_Report_{cat4}_{'-'.join(tahun)}.xlsx"
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
        from .service import get_sponsorship_outstanding
        sections, grand_total = get_sponsorship_outstanding(_cid(), filters)
        years = get_available_years(_cid())
    else:
        sections = []
        grand_total = 0.0
        years = []

    return render_template(
        "sponsorship/outstanding.html", active_page="sponsorship", use_unified_header=True,
        wrong_company=_wrong_company(),
        sections=sections, grand_total=grand_total, years=years,
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
                            wrong_company=_wrong_company(), years=years, **_ctx())

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
        download_name="Sponsorship_Data.xlsx"
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
