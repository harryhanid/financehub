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
    get_dashboard_data, get_sponsorship_report,
)
from modules.sponsorship.exports import export_report_excel
import config

bp = Blueprint("sponsorship", __name__, url_prefix="/sponsorship")

PER_PAGE = 100


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
    for key in ("cat", "cat3", "description", "status", "tahun"):
        val = request.args.get(key)
        if val:
            filters[key] = val
    return filters


def _parse_report_params():
    tahun = request.args.get("tahun") or ""
    if not tahun:
        years = get_available_years(_cid())
        tahun = years[0] if years else str(datetime.now().year)
    cat4 = (request.args.get("cat4") or "all").lower()
    if cat4 not in ("include", "exclude", "all"):
        cat4 = "all"
    return tahun, cat4


@bp.route("/")
@jwt_html_required
def index():
    years = get_available_years(_cid()) if not _wrong_company() else []
    return render_template("sponsorship/dashboard.html", active_page="sponsorship",
                            wrong_company=_wrong_company(), years=years,
                            cat_choices=config.SPONSORSHIP_CAT,
                            pillar_choices=config.SPONSORSHIP_PILLARS,
                            **_ctx())


@bp.route("/api/dashboard-data")
@jwt_html_required
@smt_company_required
def api_dashboard_data():
    data = get_dashboard_data(_cid(), _parse_filters())
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
    filename = f"Sponsorship_Report_{cat4}_{tahun}.xlsx"
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


@bp.route("/data")
@jwt_html_required
def data_page():
    filters = _parse_filters()
    total = count_transaksi(_cid(), filters) if not _wrong_company() else 0
    page = request.args.get("page", 1, type=int) or 1
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(1, min(page, total_pages))
    rows = list_transaksi(_cid(), filters, limit=PER_PAGE, offset=(page - 1) * PER_PAGE) if not _wrong_company() else []
    years = get_available_years(_cid()) if not _wrong_company() else []
    return render_template(
        "sponsorship/data.html", active_page="sponsorship", wrong_company=_wrong_company(),
        rows=rows, page=page, total_pages=total_pages, total_count=total, years=years,
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


@bp.route("/report")
@jwt_html_required
def report_page():
    return render_template("sponsorship/report.html", active_page="sponsorship",
                            wrong_company=_wrong_company(), **_ctx())
