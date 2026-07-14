from functools import wraps
from flask import Blueprint, render_template, session, jsonify, request
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
    get_available_years, get_available_pillars, get_monthly_breakdown,
)

bp = Blueprint("sahabat_etf", __name__, url_prefix="/beasiswa/sahabat")


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


def _parse_filters():
    years_param = request.args.get("years", "")
    years = [int(y) for y in years_param.split(",") if y.strip().isdigit()] if years_param else None
    pillar = request.args.get("pillar") or None
    return years, pillar


def etf_company_required(f):
    """Guard for JSON/CSV endpoints: Sahabat ETF data is ETF-only.

    The index page already shows a "Ganti Company" notice via `wrong_company`,
    but that only guards HTML rendering — it does not stop a non-ETF session
    from hitting these API/export URLs directly. Enforce it server-side here.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("company_code") != "ETF":
            return jsonify({"ok": False, "pesan": "Akses ditolak. Modul ini khusus company ETF."}), 403
        return f(*args, **kwargs)
    return decorated


@bp.route("/")
@jwt_html_required
def index():
    cid = _cid()
    return render_template(
        "sahabat_etf/index.html",
        active_page="sahabat_etf",
        wrong_company=(session.get("company_code") != "ETF"),
        available_years=get_available_years(cid),
        available_pillars=get_available_pillars(cid),
        **_ctx(),
    )


@bp.route("/api/summary")
@jwt_html_required
@etf_company_required
def api_summary():
    years, pillar = _parse_filters()
    return jsonify({"rows": get_siswa_summary(_cid(), years, pillar)})


@bp.route("/api/breakdown")
@jwt_html_required
@etf_company_required
def api_breakdown():
    years, pillar = _parse_filters()
    return jsonify(get_kategori_breakdown(_cid(), years, pillar))


@bp.route("/api/monthly")
@jwt_html_required
@etf_company_required
def api_monthly():
    years, pillar = _parse_filters()
    if not years:
        return jsonify({"ok": False, "pesan": "Parameter years wajib diisi."}), 400
    return jsonify(get_monthly_breakdown(_cid(), years, pillar))


@bp.route("/api/detail/<siswa_code>")
@jwt_html_required
@etf_company_required
def api_detail(siswa_code):
    return jsonify({"rows": get_siswa_detail(_cid(), siswa_code)})


@bp.route("/export/summary")
@jwt_html_required
@etf_company_required
def export_summary():
    import csv, io
    from flask import Response
    rows = get_siswa_summary(_cid())
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Kode", "Nama", "Jenjang", "Angkatan", "Status",
                "Budget", "Payment", "Realisasi", "Sisa Budget"])
    for r in rows:
        w.writerow([r["siswa_code"], r["nama"], r["jenjang"], r["angkatan"], r["status"],
                    r["budget_total"], r["payment_total"], r["realisasi_total"], r["sisa_budget"]])
    out.seek(0)
    return Response(out.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=sahabat_etf_ringkasan.csv"})


@bp.route("/export/detail")
@jwt_html_required
@etf_company_required
def export_detail():
    import csv, io
    from flask import Response
    rows = get_all_transactions(_cid())
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Sumber", "Kode Siswa", "Nama", "Tanggal", "Kategori 1", "Kategori 2", "Amount", "Status"])
    for r in rows:
        w.writerow([r["sumber"], r["siswa_code"], r["nama"], r["tanggal"],
                    r["cat1"], r["cat2"], r["amount"], r["status"]])
    out.seek(0)
    return Response(out.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=sahabat_etf_detail_transaksi.csv"})
