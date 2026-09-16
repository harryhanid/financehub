from functools import wraps
from flask import Blueprint, render_template, session, jsonify, request, redirect, url_for
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
    get_available_years, get_available_pillars, get_monthly_breakdown, get_latest_payments,
    get_pillar_breakdown, get_yearly_breakdown, get_family_summary, build_report_data, build_pohon_data
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
    
    # Support both pillars=A,B and pillars[]=A&pillars[]=B
    pillars_arr = request.args.getlist("pillars[]")
    if pillars_arr:
        pillars = [p for p in pillars_arr if p.strip()]
    else:
        pillars_param = request.args.get("pillars", "")
        pillars = [p for p in pillars_param.split(",") if p.strip()] if pillars_param else None
    
    return years, pillars

def _parse_report_filters():
    # Support both pillars=A,B and pillars[]=A&pillars[]=B
    pillars_arr = request.args.getlist("pillars[]")
    if pillars_arr:
        pillars = [p for p in pillars_arr if p.strip()]
    else:
        pillars_param = request.args.get("pillars", "")
        pillars = [p for p in pillars_param.split(",") if p.strip()] if pillars_param else None
    
    month_param = request.args.get("month", "12")
    month = int(month_param) if month_param.isdigit() else 12
    return month, pillars


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
    # The standalone page is now embedded as a tab in Beasiswa (see
    # templates/beasiswa/index.html's tab-sahabat panel) — redirect old
    # bookmarks/links there instead of rendering a separate page.
    return redirect(url_for("beasiswa.index", tab="sahabat"))


@bp.route("/api/summary")
@jwt_html_required
@etf_company_required
def api_summary():
    years, pillars = _parse_filters()
    return jsonify({"rows": get_siswa_summary(_cid(), years, pillars)})


@bp.route("/api/breakdown")
@jwt_html_required
@etf_company_required
def api_breakdown():
    years, pillars = _parse_filters()
    result = get_kategori_breakdown(_cid(), years, pillars)
    result["pillar"] = get_pillar_breakdown(_cid(), years, pillars)
    result["yearly"] = get_yearly_breakdown(_cid(), years, pillars)
    return jsonify(result)


@bp.route("/api/monthly")
@jwt_html_required
@etf_company_required
def api_monthly():
    years, pillars = _parse_filters()
    if not years:
        return jsonify({"ok": False, "pesan": "Parameter years wajib diisi."}), 400
    return jsonify(get_monthly_breakdown(_cid(), years, pillars))


@bp.route("/api/family_summary")
@jwt_html_required
@etf_company_required
def api_family_summary():
    years, pillars = _parse_filters()
    return jsonify({"families": get_family_summary(_cid(), years, pillars)})


@bp.route("/api/latest_payments")
@jwt_html_required
@etf_company_required
def api_latest_payments():
    years, pillars = _parse_filters()
    kategori = request.args.get("kategori") or None
    limit = 30 if kategori else 10
    return jsonify({"rows": get_latest_payments(_cid(), years, pillars, kategori=kategori, limit=limit)})


@bp.route("/api/detail/<siswa_code>")
@jwt_html_required
@etf_company_required
def api_detail(siswa_code):
    return jsonify({"rows": get_siswa_detail(_cid(), siswa_code)})


@bp.route("/api/report")
@jwt_html_required
@etf_company_required
def api_report():
    year_param = request.args.get("year", "")
    if not year_param.strip().lstrip("-").isdigit():
        return jsonify({"ok": False, "pesan": "Parameter year wajib berupa angka."}), 400
    month, pillars = _parse_report_filters()
    try:
        data = build_report_data(_cid(), int(year_param), month, pillars)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        import traceback
        with open("C:/Financehub/last_500_error.txt", "w") as errf:
            errf.write(traceback.format_exc())
        return jsonify({"ok": False, "pesan": str(e)}), 500


@bp.route("/api/pohon")
@jwt_html_required
@etf_company_required
def api_pohon():
    years = request.args.getlist("years[]")
    if not years:
        years_csv = request.args.get("years", "")
        if years_csv:
            years = [y.strip() for y in years_csv.split(",")]

    parsed_years = []
    for y in years:
        if y.lower() in ("all", "semua"):
            parsed_years = None
            break
        elif y.isdigit():
            parsed_years.append(int(y))
    
    if parsed_years is not None and not parsed_years:
        parsed_years = None

    month, pillars = _parse_report_filters()
    from .service import build_pohon_data, build_pohon_group_data
    return jsonify({
        "ok": True,
        "data": {
            "diagram1": build_pohon_data(_cid(), parsed_years, month, pillars),
            "diagram2": build_pohon_group_data(_cid(), parsed_years, month, pillars)
        }
    })


@bp.route("/api/all_transactions")
@jwt_html_required
@etf_company_required
def api_all_transactions():
    years, pillars = _parse_filters()
    return jsonify({"ok": True, "rows": get_all_transactions(_cid(), years, pillars)})


@bp.route("/export/summary")
@jwt_html_required
@etf_company_required
def export_summary():
    import csv, io
    from flask import Response
    years, pillars = _parse_filters()
    rows = get_siswa_summary(_cid(), years, pillars)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Kode", "Nama", "Jenjang", "Angkatan", "Status",
                "Budget", "Klaim", "Realisasi", "Sisa Budget"])
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
    import io
    from flask import send_file
    from modules.sahabat_etf.report_xlsx import build_detail_workbook
    
    years, pillars = _parse_filters()
    rows = get_all_transactions(_cid(), years, pillars)
    
    xlsx_bytes = build_detail_workbook(rows)
    filename = "sahabat_etf_detail_transaksi.xlsx"
    return send_file(
        io.BytesIO(xlsx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )


@bp.route("/export/detail/csv")
@jwt_html_required
@etf_company_required
def export_detail_csv():
    import csv, io
    from flask import Response
    years, pillars = _parse_filters()
    rows = get_all_transactions(_cid(), years, pillars)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Sumber", "Kode Siswa", "Nama", "Tanggal", "Kategori 1", "Kategori 2", "Pillar", "Amount", "Status"])
    for r in rows:
        w.writerow([r["sumber"], r["siswa_code"], r["nama"], r["tanggal"],
                    r["cat1"], r["cat2"], r["pillar"], r["amount"], r["status"]])
    out.seek(0)
    return Response(out.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=sahabat_etf_detail_transaksi.csv"})


@bp.route("/export/report/detail")
@jwt_html_required
@etf_company_required
def export_report_detail():
    import io
    from flask import send_file
    from modules.sahabat_etf.report_xlsx import build_detail_workbook
    from modules.sahabat_etf.service import get_report_detail_transactions

    year_param = request.args.get("year", "")
    try:
        report_year = int(year_param.strip())
    except ValueError:
        return jsonify({"ok": False, "pesan": "Parameter year wajib berupa angka."}), 400

    month, pillars = _parse_report_filters()
    rows = get_report_detail_transactions(_cid(), report_year, month, pillars)
    
    xlsx_bytes = build_detail_workbook(rows)
    filename = f"sahabat_etf_report_detail_{report_year}_{month:02d}.xlsx"
    return send_file(
        io.BytesIO(xlsx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )


@bp.route("/export/report")
@jwt_html_required
@etf_company_required
def export_report():
    import io
    from flask import send_file
    from modules.sahabat_etf.report_xlsx import build_report_workbook

    year_param = request.args.get("year", "")
    try:
        report_year = int(year_param.strip())
    except ValueError:
        return jsonify({"ok": False, "pesan": "Parameter year wajib berupa angka."}), 400

    month, pillars = _parse_report_filters()
    data = build_report_data(_cid(), report_year, month, pillars)
    xlsx_bytes = build_report_workbook(data)
    filename = f"sahabat_etf_report_{report_year}.xlsx"
    return send_file(
        io.BytesIO(xlsx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )

@bp.route("/api/report/export_ppt", methods=["GET"])
@etf_company_required
def export_ppt_report():
    import io
    from flask import send_file
    from modules.sahabat_etf.report_pptx import build_report_pptx
    
    year_param = request.args.get("year", "")
    mode = request.args.get("mode", "ytd")
    try:
        report_year = int(year_param.strip())
    except ValueError:
        return jsonify({"ok": False, "pesan": "Parameter year wajib berupa angka."}), 400
        
    month, pillars = _parse_report_filters()
    data = build_report_data(_cid(), report_year, month, pillars)
    pptx_bytes = build_report_pptx(data, mode)
    filename = f"sahabat_etf_report_{mode}_{report_year}.pptx"
    
    return send_file(
        io.BytesIO(pptx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        as_attachment=True,
        download_name=filename
    )
