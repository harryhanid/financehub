from format_utils import format_rupiah
# modules/beasiswa/routes.py
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, Response
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required, role_required
from modules.beasiswa.service import (get_budget_requests, approve_budget_request_batch, reject_budget_request_batch,
    generate_kode_siswa, get_siswa_list, get_siswa_detail,
    add_siswa, update_siswa, update_siswa_catatan, update_siswa_catatan_payment, delete_siswa,
    add_budget_batch, get_budget, delete_budget_row, update_budget_row,
    add_payment_batch, add_payment_multi, get_payment, get_payment_list, delete_payment_row,
    update_payment_row,
    get_sisa_budget, get_rekap, get_budget_list, get_laporan_siswa,
    get_financial_summary,
    add_klaim_multi, get_klaim_list, delete_klaim_row,
    get_vendors, get_distinct_universitas, get_distinct_angkatan,
    get_dashboard_summary, get_dashboard_breakdown, get_dashboard_monthly,
    get_dashboard_latest_payments, get_dashboard_program_summary, get_dashboard_pillar_yearly,
)
from modules.sahabat_etf.service import get_available_years, get_available_pillars
import config

bp = Blueprint("beasiswa", __name__, url_prefix="/beasiswa")


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
    return session.get("company_code") != "ETF"


def etf_company_required(f):
    """Beasiswa data is ETF-only. The index page shows a "Ganti Company"
    notice via `wrong_company`, but that only guards HTML rendering — it does
    not stop a non-ETF session from hitting these API/mutating/export URLs
    directly (see the Sponsorship/Sahabat ETF precedent). Enforce it
    server-side here. `vendor_list_api` is intentionally excluded — the
    `vendors` table is a global lookup, not scoped by company_id."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("company_code") != "ETF":
            return jsonify({"ok": False, "pesan": "Akses ditolak. Modul ini khusus company ETF."}), 403
        return f(*args, **kwargs)
    return decorated


@bp.route("/")
def index():
    tab = request.args.get("tab")
    
    # Intercept public access for sahabat tab
    if tab == "sahabat":
        if session.get("public_sahabat_access"):
            return render_template(
                "sahabat_etf/public_index.html",
                available_years=get_available_years(2),
                available_pillars=get_available_pillars(2)
            )
            
        try:
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request()
        except Exception:
            return redirect(url_for("sahabat_etf.public_login"))
    else:
        try:
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request()
        except Exception:
            return redirect(url_for("auth.login_page"))

    if not _cid():
        return redirect(url_for("dashboard.select_company"))
    wrong_company = _wrong_company()
    return render_template(
        "beasiswa/index.html",
        siswa_list=get_siswa_list(_cid()) if not wrong_company else [],
        jenjang=config.JENJANG,
        program=config.PROGRAM,
        status_siswa=config.STATUS_SISWA,
        pillar=config.PILLAR,
        dashboard_pillars=config.DASHBOARD_PILLAR,
        cat1_bgt=config.CAT1_BGT,
        cat2_sem=config.CAT2_SEM,
        perusahaan=config.PERUSAHAAN,
        vendor_list=get_vendors(),
        universitas_list=get_distinct_universitas(_cid()) if not wrong_company else [],
        angkatan_list=get_distinct_angkatan(_cid()) if not wrong_company else [],
        cat3_medical=config.CAT3_MEDICAL,
        active_page="beasiswa",
        use_unified_header=True,
        wrong_company=wrong_company,
        available_years=get_available_years(_cid()) if not wrong_company else [],
        available_pillars=get_available_pillars(_cid()) if not wrong_company else [],
        **_ctx()
    )


@bp.route("/siswa/generate-kode")
@jwt_html_required
@etf_company_required
def siswa_generate_kode():
    jenjang  = request.args.get("jenjang", "").strip()
    angkatan = request.args.get("angkatan", "").strip()
    if not jenjang or not angkatan.isdigit() or len(angkatan) != 4:
        return jsonify({"ok": False, "pesan": "Jenjang dan angkatan (4 digit) wajib diisi."})
    kode = generate_kode_siswa(jenjang, int(angkatan), _cid())
    return jsonify({"ok": True, "kode": kode})


@bp.route("/siswa/tambah", methods=["POST"])
@role_required("FC", "Admin")
@etf_company_required
def siswa_tambah():
    return jsonify(add_siswa(_cid(), request.get_json(force=True) or {}))


@bp.route("/siswa/<code>")
@jwt_html_required
@etf_company_required
def siswa_detail(code):
    row = get_siswa_detail(_cid(), code)
    if not row:
        return jsonify({"ok": False, "pesan": "Tidak ditemukan."})
    return jsonify({"ok": True, "data": row})


@bp.route("/siswa/<code>/update", methods=["POST"])
@role_required("FC", "Fin", "Admin")
@etf_company_required
def siswa_update(code):
    return jsonify(update_siswa(_cid(), code, request.get_json(force=True) or {}))


@bp.route("/siswa/<code>/catatan", methods=["POST"])
@role_required("FC", "Admin")
@etf_company_required
def siswa_catatan_update(code):
    data = request.get_json(force=True) or {}
    return jsonify(update_siswa_catatan(_cid(), code, data.get("catatan", "")))


@bp.route("/siswa/<code>/catatan-payment", methods=["POST"])
@role_required("FC", "Admin")
@etf_company_required
def siswa_catatan_payment_update(code):
    data = request.get_json(force=True) or {}
    return jsonify(update_siswa_catatan_payment(_cid(), code, data.get("catatan_payment", "")))


@bp.route("/siswa/<code>/hapus", methods=["POST"])
@role_required("FC", "Admin")
@etf_company_required
def siswa_hapus(code):
    return jsonify(delete_siswa(_cid(), code))


@bp.route("/siswa/<code>/sisa-budget")
@jwt_html_required
@etf_company_required
def siswa_sisa_budget(code):
    sisa = get_sisa_budget(_cid(), code)
    return jsonify({"ok": True, **sisa})


@bp.route("/budget/siswa/<code>")
@jwt_html_required
@etf_company_required
def budget_by_siswa(code):
    result = get_budget(_cid(), code)
    siswa  = get_siswa_detail(_cid(), code)
    return jsonify({"ok": True, "nama": siswa["nama"] if siswa else "",
                    "catatan_budget": (siswa["catatan_budget"] or "") if siswa else "", **result})


@bp.route("/budget/siswa/<code>/export/<fmt>")
@jwt_html_required
@etf_company_required
def budget_siswa_export(code, fmt):
    result = get_budget(_cid(), code)
    siswa  = get_siswa_detail(_cid(), code)
    nama   = siswa["nama"] if siswa else code
    rows   = result.get("rows", [])
    grand  = result.get("grand", 0)

    if fmt == "csv":
        import csv, io
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["Budget Siswa"])
        w.writerow(["Kode", code, "Nama", nama, "Perusahaan", session.get("company_name", "")])
        w.writerow([])
        w.writerow(["Kategori 1", "Kategori 2", "Tanggal", "Pillar", "Amount"])
        for r in rows:
            w.writerow([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                        r.get("pillar",""), r.get("amount", 0)])
        if rows:
            w.writerow(["TOTAL", "", "", "", grand])
        out.seek(0)
        return Response(out.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename=budget_{code}.csv"})

    if fmt == "pdf":
        import io
        from flask import send_file
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()
        elems = [Paragraph(f"Budget Siswa — {nama} ({code})", styles["Title"]),
                 Paragraph(session.get("company_name", ""), styles["Normal"]),
                 Spacer(1, 0.5*cm)]
        data = [["No", "Kategori 1", "Kategori 2", "Tanggal", "Pillar", "Amount (Rp)"]]
        for i, r in enumerate(rows, 1):
            data.append([i, r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                         r.get("pillar",""), format_rupiah(r.get('amount',0), prefix="")])
        if rows:
            data.append(["", "TOTAL", "", "", "", format_rupiah(grand, prefix="")])
        tbl = Table(data, colWidths=[1*cm, 3.5*cm, 4*cm, 2.5*cm, 3*cm, 3*cm], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a56db")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
            ("ALIGN", (5,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        elems.append(tbl)
        doc.build(elems)
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf",
                         download_name=f"budget_{code}.pdf", as_attachment=True)

    return ("Format tidak dikenal.", 400)


@bp.route("/budget/<int:row_id>/hapus", methods=["POST"])
@role_required("FC", "Admin")
@etf_company_required
def budget_hapus(row_id):
    return jsonify(delete_budget_row(_cid(), row_id, _ctx()["current_user"]))


@bp.route("/budget/<int:row_id>/update", methods=["POST"])
@role_required("FC", "Admin")
@etf_company_required
def budget_update_row(row_id):
    return jsonify(update_budget_row(_cid(), row_id, request.get_json(force=True) or {}, _ctx()["current_user"]))


@bp.route("/budget/tambah", methods=["POST"])
@role_required("FC", "Admin")
@etf_company_required
def budget_tambah():
    data   = request.get_json(force=True) or {}
    code   = (data.get("code") or "").strip()
    if not code:
        return jsonify({"ok": False, "pesan": "Code siswa wajib diisi."})
    return jsonify(add_budget_batch(_cid(), code, data.get("tanggal", ""), data.get("pillar", ""), data.get("items", []), _ctx()["current_user"]))


@bp.route("/vendors")
@jwt_html_required
def vendor_list_api():
    search = request.args.get("search", "").strip()
    return jsonify({"ok": True, "rows": get_vendors(search)})


@bp.route("/summary")
@jwt_html_required
@etf_company_required
def financial_summary():
    return jsonify({"ok": True, **get_financial_summary(_cid())})


@bp.route("/budget/list")
@jwt_html_required
@etf_company_required
def budget_list():
    data = get_budget_list(
        _cid(),
        search=request.args.get("search", ""),
        cat1=request.args.get("cat1", ""),
        pillar=request.args.get("pillar", ""),
        bulan=request.args.get("bulan", ""),
        tahun=request.args.get("tahun", ""),
        program=request.args.get("program", ""),
    )
    return jsonify({"ok": True, **data})


@bp.route("/budget/export/xlsx")
@bp.route("/budget/export/excel")
@jwt_html_required
@etf_company_required
def budget_export_xlsx():
    from modules.beasiswa.exports import export_budget_excel
    import io
    from flask import send_file
    from datetime import datetime

    search = request.args.get("search", "")
    cat1 = request.args.get("cat1", "")
    pillar = request.args.get("pillar", "")
    bulan = request.args.get("bulan", "")
    tahun = request.args.get("tahun", "")
    program = request.args.get("program", "")

    xls_bytes = export_budget_excel(
        _cid(),
        search=search,
        cat1=cat1,
        pillar=pillar,
        bulan=bulan,
        tahun=tahun,
        program=program,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Budget_Beasiswa_ETF_{timestamp}.xlsx"
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )


@bp.route("/api/dashboard/export_kategori")
@jwt_html_required
@etf_company_required
def api_dashboard_export_kategori():
    from modules.beasiswa.exports import export_dashboard_kategori_excel
    import io
    from flask import send_file
    from datetime import datetime

    cat1 = request.args.get("cat1", "").strip() or None

    years_str = request.args.get("years", "")
    years = [int(y) for y in years_str.split(",") if y.isdigit()] if years_str else None

    pillars_str = request.args.get("pillars", "")
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs_str = request.args.get("jenjangs", "")
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    angkatans_str = request.args.get("angkatans", "")
    angkatans = [a for a in angkatans_str.split(",") if a]
    statuses_str = request.args.get("statuses", "")
    statuses = [s for s in statuses_str.split(",") if s]

    xls_bytes = export_dashboard_kategori_excel(
        _cid(),
        cat1=cat1,
        years=years,
        pillars=pillars,
        programs=programs,
        jenjangs=jenjangs,
        statuses=statuses,
        angkatans=angkatans,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if cat1:
        cat_clean = cat1.replace(" ", "_").replace("/", "_")
        filename = f"Realisasi_Kategori_{cat_clean}_{timestamp}.xlsx"
    else:
        filename = f"Realisasi_Per_Kategori_ETF_{timestamp}.xlsx"

    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )


@bp.route("/api/dashboard/export_trend_bulanan")
@jwt_html_required
@etf_company_required
def api_dashboard_export_trend_bulanan():
    from modules.beasiswa.exports import export_dashboard_bulanan_excel
    import io
    from flask import send_file
    from datetime import datetime

    bulan_str = request.args.get("bulan", "").strip()
    bulan = int(bulan_str) if (bulan_str and bulan_str.isdigit()) else None

    years_str = request.args.get("years", "")
    years = [int(y) for y in years_str.split(",") if y.isdigit()] if years_str else None

    pillars_str = request.args.get("pillars", "")
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs_str = request.args.get("jenjangs", "")
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    angkatans_str = request.args.get("angkatans", "")
    angkatans = [a for a in angkatans_str.split(",") if a]
    statuses_str = request.args.get("statuses", "")
    statuses = [s for s in statuses_str.split(",") if s]

    xls_bytes = export_dashboard_bulanan_excel(
        _cid(),
        bulan=bulan,
        years=years,
        pillars=pillars,
        programs=programs,
        jenjangs=jenjangs,
        statuses=statuses,
        angkatans=angkatans,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bulan_names = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    if bulan and 1 <= bulan <= 12:
        filename = f"Trend_Realisasi_Bulanan_{bulan_names[bulan]}_{timestamp}.xlsx"
    else:
        filename = f"Trend_Realisasi_Bulanan_ETF_{timestamp}.xlsx"

    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )


@bp.route("/budget/export/csv")
@jwt_html_required
@etf_company_required
def budget_export_csv():
    import csv, io
    rows = get_budget_list(_cid(),
        search=request.args.get("search",""), cat1=request.args.get("cat1",""),
        pillar=request.args.get("pillar",""), bulan=request.args.get("bulan",""),
        tahun=request.args.get("tahun",""), program=request.args.get("program",""),
        limit=100000)["rows"]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Kode","Nama","Program","Kategori 1","Kategori 2","Tanggal","Pillar","Amount"])
    for r in rows:
        w.writerow([r.get("siswa_code",""), r.get("nama",""), r.get("program",""),
                    r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                    r.get("pillar",""), r.get("amount",0)])
    out.seek(0)
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=budget_beasiswa.csv"})


@bp.route("/budget/export/pdf")
@jwt_html_required
@etf_company_required
def budget_export_pdf():
    import io
    from flask import send_file
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    rows = get_budget_list(_cid(),
        search=request.args.get("search",""), cat1=request.args.get("cat1",""),
        pillar=request.args.get("pillar",""), bulan=request.args.get("bulan",""),
        tahun=request.args.get("tahun",""), program=request.args.get("program",""),
        limit=100000)["rows"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elems  = [Paragraph(f"Data Budget Beasiswa — {session.get('company_name','')}", styles["Title"]),
              Spacer(1, 0.4*cm)]
    data = [["No","Kode","Nama","Program","Kategori 1","Kategori 2","Tanggal","Pillar","Amount"]]
    total = 0
    for i, r in enumerate(rows, 1):
        a = r.get("amount",0); total += a
        data.append([i, r.get("siswa_code",""), r.get("nama",""), r.get("program",""),
                     r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                     r.get("pillar",""), format_rupiah(a, prefix="")])
    if rows:
        data.append(["","","TOTAL","","","","","",format_rupiah(total, prefix="")])
    tbl = Table(data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#1a56db")),
        ("TEXTCOLOR",(0,0),(-1,0), colors.white),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 7),
        ("ALIGN",(8,0),(-1,-1), "RIGHT"),
        ("GRID",(0,0),(-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ("BACKGROUND",(0,-1),(-1,-1), colors.HexColor("#f3f4f6")),
        ("FONTNAME",(0,-1),(-1,-1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    elems.append(tbl)
    doc.build(elems)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf",
                     download_name="budget_beasiswa.pdf", as_attachment=True)


@bp.route("/payment/list")
@jwt_html_required
@etf_company_required
def payment_list():
    data = get_payment_list(
        _cid(),
        search=request.args.get("search", ""),
        bulan=request.args.get("bulan", ""),
        tahun=request.args.get("tahun", ""),
        status=request.args.get("status", ""),
        cat1=request.args.get("cat1", ""),
        pillar=request.args.get("pillar", ""),
        program=request.args.get("program", ""),
    )
    return jsonify({"ok": True, **data})


@bp.route("/payment/export/xlsx")
@bp.route("/payment/export/excel")
@jwt_html_required
@etf_company_required
def payment_export_xlsx():
    from modules.beasiswa.exports import export_payment_excel
    import io
    from flask import send_file
    from datetime import datetime

    search = request.args.get("search", "")
    cat1 = request.args.get("cat1", "")
    pillar = request.args.get("pillar", "")
    bulan = request.args.get("bulan", "")
    tahun = request.args.get("tahun", "")
    status = request.args.get("status", "")
    program = request.args.get("program", "")

    xls_bytes = export_payment_excel(
        _cid(),
        search=search,
        cat1=cat1,
        pillar=pillar,
        bulan=bulan,
        tahun=tahun,
        status=status,
        program=program,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Payment_Beasiswa_ETF_{timestamp}.xlsx"
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )


@bp.route("/payment/export/csv")
@jwt_html_required
@etf_company_required
def payment_export_csv():
    import csv, io
    rows = get_payment_list(_cid(),
        search=request.args.get("search",""), cat1=request.args.get("cat1",""),
        pillar=request.args.get("pillar",""), bulan=request.args.get("bulan",""),
        tahun=request.args.get("tahun",""), status=request.args.get("status",""),
        program=request.args.get("program",""), limit=100000)["rows"]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Kode","Nama","Program","Kategori 1","Kategori 2","Tanggal","Pillar","Amount","PAM","Perusahaan","Status"])
    for r in rows:
        w.writerow([r.get("siswa_code",""), r.get("nama",""), r.get("program",""),
                    r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                    r.get("pillar",""), r.get("amount",0),
                    r.get("pam",""), r.get("perusahaan",""), r.get("status","")])
    out.seek(0)
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=payment_beasiswa.csv"})


@bp.route("/payment/export/pdf")
@jwt_html_required
@etf_company_required
def payment_export_pdf():
    import io
    from flask import send_file
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    rows = get_payment_list(_cid(),
        search=request.args.get("search",""), cat1=request.args.get("cat1",""),
        pillar=request.args.get("pillar",""), bulan=request.args.get("bulan",""),
        tahun=request.args.get("tahun",""), status=request.args.get("status",""),
        program=request.args.get("program",""), limit=100000)["rows"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elems  = [Paragraph(f"Data Payment Beasiswa — {session.get('company_name','')}", styles["Title"]),
              Spacer(1, 0.4*cm)]
    data = [["No","Kode","Nama","Program","Kategori 1","Kategori 2","Tanggal","Pillar","Amount","PAM","Perusahaan","Status"]]
    total = 0
    for i, r in enumerate(rows, 1):
        a = r.get("amount",0); total += a
        data.append([i, r.get("siswa_code",""), r.get("nama",""), r.get("program",""),
                     r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                     r.get("pillar",""), format_rupiah(a, prefix=""),
                     r.get("pam",""), r.get("perusahaan",""), r.get("status","")])
    if rows:
        data.append(["","","TOTAL","","","","","",format_rupiah(total, prefix=""),"","",""])
    tbl = Table(data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#065f46")),
        ("TEXTCOLOR",(0,0),(-1,0), colors.white),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 7),
        ("ALIGN",(8,0),(8,-1), "RIGHT"),
        ("GRID",(0,0),(-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ("BACKGROUND",(0,-1),(-1,-1), colors.HexColor("#f3f4f6")),
        ("FONTNAME",(0,-1),(-1,-1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    elems.append(tbl)
    doc.build(elems)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf",
                     download_name="payment_beasiswa.pdf", as_attachment=True)


@bp.route("/payment/<int:row_id>/hapus", methods=["POST"])
@role_required("FC", "Admin")
@etf_company_required
def payment_hapus(row_id):
    return jsonify(delete_payment_row(_cid(), row_id))


@bp.route("/payment/<int:row_id>/edit", methods=["POST"])
@role_required("FC", "Admin")
@etf_company_required
def payment_edit(row_id):
    data = request.get_json(force=True) or {}
    return jsonify(update_payment_row(
        _cid(), row_id,
        pam=data.get("pam"),
        tanggal_bayar=data.get("tanggal_bayar"),
    ))


@bp.route("/payment/tambah", methods=["POST"])
@role_required("FC", "Admin")
@etf_company_required
def payment_tambah():
    data   = request.get_json(force=True) or {}
    code   = (data.get("code") or "").strip()
    if not code:
        return jsonify({"ok": False, "pesan": "Code siswa wajib diisi."})
    return jsonify(add_payment_batch(_cid(), code,
        data.get("tanggal", ""), data.get("pillar", ""),
        data.get("perusahaan", ""), data.get("items", [])))


@bp.route("/payment/tambah-multi", methods=["POST"])
@role_required("FC", "Admin")
@etf_company_required
def payment_tambah_multi():
    data = request.get_json(force=True) or {}
    rows = data.get("rows", [])
    if not rows:
        return jsonify({"ok": False, "pesan": "Tidak ada baris untuk disimpan."})
    return jsonify(add_payment_multi(
        _cid(),
        session.get("company_code", ""),
        data.get("tanggal", ""),
        data.get("pillar", ""),
        data.get("perusahaan", ""),
        rows,
    ))


@bp.route("/klaim/list")
@jwt_html_required
@etf_company_required
def klaim_list():
    data = get_klaim_list(
        _cid(),
        search=request.args.get("search", ""),
        bulan=request.args.get("bulan", ""),
        tahun=request.args.get("tahun", ""),
        perawatan=request.args.get("perawatan", ""),
    )
    return jsonify({"ok": True, **data})


@bp.route("/klaim/tambah-multi", methods=["POST"])
@role_required("FC", "Admin")
@etf_company_required
def klaim_tambah_multi():
    data = request.get_json(force=True) or {}
    rows = data.get("rows", [])
    if not rows:
        return jsonify({"ok": False, "pesan": "Tidak ada baris untuk disimpan."})
    return jsonify(add_klaim_multi(
        _cid(),
        data.get("pam", ""),
        data.get("pillar", ""),
        data.get("perusahaan", ""),
        rows,
    ))


@bp.route("/klaim/<int:row_id>/hapus", methods=["POST"])
@role_required("FC", "Admin")
@etf_company_required
def klaim_hapus(row_id):
    return jsonify(delete_klaim_row(_cid(), row_id))


@bp.route("/laporan/siswa/<code>")
@jwt_html_required
@etf_company_required
def laporan_siswa(code):
    data = get_laporan_siswa(_cid(), code)
    if not data:
        return jsonify({"ok": False, "pesan": "Siswa tidak ditemukan."})
    return jsonify({"ok": True, **data})


@bp.route("/laporan/siswa/<code>/export/<fmt>")
@jwt_html_required
@etf_company_required
def laporan_export(code, fmt):
    data = get_laporan_siswa(_cid(), code)
    if not data:
        return ("Siswa tidak ditemukan.", 404)
    s = data["siswa"]

    if fmt == "csv":
        import csv, io
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["=== DATA SISWA ==="])
        w.writerow(["Kode", s.get("code",""), "Nama", s.get("nama","")])
        w.writerow(["Jenjang", s.get("jenjang",""), "Angkatan", s.get("angkatan",""), "Program", s.get("program","")])
        w.writerow(["Universitas", s.get("universitas",""), "Fakultas", s.get("fakultas",""), "Status", s.get("status","")])
        w.writerow(["Bank", s.get("bank",""), "No. Rekening", s.get("norek",""), "Nama Rekening", s.get("namarek","")])
        w.writerow(["Referensi", s.get("referensi",""), "Catatan", s.get("catatan","")])
        ipk_sems = [(i, s.get(f"ipk_sem{i}","")) for i in range(1,11) if s.get(f"ipk_sem{i}")]
        if ipk_sems:
            w.writerow(["IPK Semester"] + [f"Sem {i}: {v}" for i, v in ipk_sems])
        ipk_pens = [(i, s.get(f"ipk_pen{i}","")) for i in range(1,4) if s.get(f"ipk_pen{i}")]
        if ipk_pens:
            w.writerow(["IPK Penelitian"] + [f"Tahap {i}: {v}" for i, v in ipk_pens])
        w.writerow([])
        w.writerow(["=== REKAPITULASI PER KATEGORI ==="])
        w.writerow(["Kategori", "Budget", "Payment", "Selisih"])
        for c in data["cat_summary"]:
            w.writerow([c["cat1"], c["budget"], c["payment"], c["sisa"]])
        w.writerow(["TOTAL", data["total_budget"], data["total_payment"], data["total_sisa"]])
        w.writerow([])
        w.writerow(["=== DETAIL BUDGET ==="])
        w.writerow(["Kategori 1", "Kategori 2", "Tanggal", "Pillar", "Amount"])
        bgt_total = 0
        for r in data["budget_rows"]:
            a = r.get("amount", 0); bgt_total += a
            w.writerow([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                        r.get("pillar",""), a])
        w.writerow(["", "", "", "Subtotal", bgt_total])
        w.writerow([])
        w.writerow(["=== DETAIL PAYMENT ==="])
        w.writerow(["Kategori 1", "Kategori 2", "Tanggal", "PAM", "Perusahaan", "Pillar", "Amount", "Status"])
        pay_total = 0
        for r in data["payment_rows"]:
            a = r.get("amount", 0); pay_total += a
            w.writerow([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                        r.get("pam",""), r.get("perusahaan",""), r.get("pillar",""), a, r.get("status","")])
        w.writerow(["", "", "", "", "", "Subtotal", pay_total, ""])
        out.seek(0)
        fname = f"laporan_{code}.csv"
        return Response(out.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={fname}"})

    if fmt == "pdf":
        import io, os
        from datetime import date as _date
        from flask import send_file
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.enums import TA_RIGHT

        # ── FLOW brand palette (exact hex values used elsewhere in the app) ──
        COBALT      = colors.HexColor("#5B8CFF")
        INK_DARK    = colors.HexColor("#0F1220")
        INK         = colors.HexColor("#1e293b")
        MUTED       = colors.HexColor("#64748b")
        HAIRLINE    = colors.HexColor("#f1f5f9")
        COBALT_TINT = colors.HexColor("#eff6ff")
        GREEN       = colors.HexColor("#047857")
        GREEN_TINT  = colors.HexColor("#ecfdf5")
        GREEN_LINE  = colors.HexColor("#10b981")
        NEGATIVE    = colors.HexColor("#dc2626")
        FLOW_MARK_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "static", "img", "flow-mark.png")

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()

        # Text wrapping style for tables
        cell_style = styles["Normal"].clone('cell_style')
        cell_style.fontSize = 8
        cell_style.leading = 10
        cell_style.wordWrap = 'CJK'

        amount_cell_style = cell_style.clone('amount_cell_style')
        amount_cell_style.alignment = TA_RIGHT

        label_style = cell_style.clone('label_style')
        label_style.fontName = 'Helvetica-Bold'
        label_style.fontSize = 7
        label_style.textColor = MUTED

        def wrap_row(row, is_header=False, is_footer=False, amount_col=None):
            wrapped = []
            for i, item in enumerate(row):
                if is_header or is_footer:
                    wrapped.append(item)
                else:
                    style = amount_cell_style if i == amount_col else cell_style
                    wrapped.append(Paragraph(str(item), style) if item else "")
            return wrapped

        def _lv_row(label1, value1, label2, value2):
            return [
                Paragraph(str(label1).upper(), label_style),
                Paragraph(str(value1), cell_style) if value1 else "",
                Paragraph(str(label2).upper(), label_style) if label2 else "",
                Paragraph(str(value2), cell_style) if value2 else "",
            ]

        section_title_style = styles["Normal"].clone('section_title')
        section_title_style.fontName = 'Helvetica-Bold'
        section_title_style.fontSize = 9
        section_title_style.textColor = INK

        def section_header(text, accent=COBALT):
            """Small bold uppercase heading with a left accent rule."""
            tbl = Table([[Paragraph(text.upper(), section_title_style)]])
            tbl.setStyle(TableStyle([
                ("LINEBEFORE", (0,0), (0,0), 2.5, accent),
                ("LEFTPADDING", (0,0), (0,0), 8),
                ("TOPPADDING", (0,0), (-1,-1), 0),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ]))
            return tbl

        # ── Letterhead ──────────────────────────────────────────────────
        brand_style = styles["Normal"].clone('brand_style')
        brand_style.fontName = 'Helvetica-Bold'
        brand_style.fontSize = 13
        brand_style.textColor = INK_DARK

        company_style = styles["Normal"].clone('company_style')
        company_style.fontSize = 8
        company_style.textColor = MUTED
        company_style.alignment = TA_RIGHT
        company_style.leading = 11

        try:
            mark = Image(FLOW_MARK_PATH, width=18, height=18)
        except Exception:
            mark = ""

        header_tbl = Table(
            [[mark, Paragraph("FLOW", brand_style),
              Paragraph(f"{session.get('company_name','')}<br/>Dicetak {_date.today().strftime('%d %B %Y')}", company_style)]],
            colWidths=[1.2*cm, 3*cm, None],
        )
        header_tbl.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LINEBELOW", (0,0), (-1,-1), 1.4, INK_DARK),
            ("TOPPADDING", (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING", (0,0), (0,0), 0),
        ]))

        title_style = styles["Normal"].clone('report_title')
        title_style.fontName = 'Helvetica-Bold'
        title_style.fontSize = 16
        title_style.textColor = INK_DARK
        title_style.spaceBefore = 12
        title_style.spaceAfter = 6

        subtitle_style = styles["Normal"].clone('report_subtitle')
        subtitle_style.fontSize = 9
        subtitle_style.textColor = MUTED
        subtitle_style.spaceAfter = 14

        elems = [
            header_tbl,
            Paragraph("Laporan Siswa", title_style),
            Paragraph(f"{s.get('nama','')} &middot; {s.get('code','')}", subtitle_style),
        ]

        # Student info table (2-column label/value pairs)
        elems.append(section_header("Data Siswa"))
        info_rows = [
            _lv_row("Kode Siswa", s.get("code",""),          "Status", s.get("status","")),
            _lv_row("Nama",       s.get("nama",""),           "Program", s.get("program","")),
            _lv_row("Jenjang",    s.get("jenjang",""),        "Angkatan", str(s.get("angkatan",""))),
            _lv_row("Universitas",s.get("universitas",""),    "Fakultas", s.get("fakultas","")),
            _lv_row("Bank",       s.get("bank",""),           "No. Rekening", s.get("norek","")),
            _lv_row("Nama Rek.",  s.get("namarek",""),        "Referensi", s.get("referensi","")),
        ]
        if s.get("catatan"):
            info_rows.append(_lv_row("Catatan", s.get("catatan",""), "", ""))
        info_tbl = Table(info_rows, colWidths=[2.5*cm, 5.5*cm, 2.5*cm, 6.5*cm])
        info_tbl.setStyle(TableStyle([
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("LINEBELOW",  (0,0), (-1,-1), 0.5, HAIRLINE),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING", (0,0), (0,-1), 0),
        ]))
        elems += [info_tbl, Spacer(1, 0.5*cm)]

        # IPK section
        ipk_sems = [(i, s.get(f"ipk_sem{i}")) for i in range(1,11) if s.get(f"ipk_sem{i}")]
        ipk_pens = [(i, s.get(f"ipk_pen{i}")) for i in range(1,4) if s.get(f"ipk_pen{i}")]
        if ipk_sems or ipk_pens:
            elems.append(section_header("IPK"))
            ipk_rows = []
            if ipk_sems:
                ipk_rows.append(["IPK Semester"] + [f"Sem {i}: {float(v):.2f}" for i, v in ipk_sems])
            if ipk_pens:
                ipk_rows.append(["IPK Penelitian"] + [f"Tahap {i}: {float(v):.2f}" for i, v in ipk_pens])
            max_cols = max(len(r) for r in ipk_rows)
            for r in ipk_rows:
                while len(r) < max_cols:
                    r.append("")
            ipk_rows = [
                [Paragraph(str(row[0]).upper(), label_style)] +
                [Paragraph(str(v), cell_style) if v else "" for v in row[1:]]
                for row in ipk_rows
            ]
            ipk_tbl = Table(ipk_rows)
            ipk_tbl.setStyle(TableStyle([
                ("FONTSIZE",   (0,0), (-1,-1), 8),
                ("LINEBELOW",  (0,0), (-1,-1), 0.5, HAIRLINE),
                ("TOPPADDING", (0,0), (-1,-1), 3),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3),
                ("LEFTPADDING", (0,0), (0,-1), 0),
            ]))
            elems += [ipk_tbl, Spacer(1, 0.5*cm)]

        # Summary table
        elems.append(section_header("Rekapitulasi per Kategori"))
        sum_data = [["Kategori", "Budget (Rp)", "Payment (Rp)", "Selisih (Rp)"]]
        for c in data["cat_summary"]:
            kategori_cell = Paragraph(str(c["cat1"]), cell_style) if c["cat1"] else ""
            sum_data.append([kategori_cell, format_rupiah(c['budget'], prefix=""), format_rupiah(c['payment'], prefix=""), format_rupiah(c['sisa'], prefix="")])
        sum_data.append(["TOTAL", format_rupiah(data['total_budget'], prefix=""),
                         format_rupiah(data['total_payment'], prefix=""), format_rupiah(data['total_sisa'], prefix="")])
        st = Table(sum_data, colWidths=[5*cm, 4*cm, 4*cm, 4*cm])
        neg_rows = [i+1 for i, c in enumerate(data["cat_summary"]) if c["sisa"] < 0]
        ts = TableStyle([
            ("BACKGROUND", (0,0), (-1,0), INK_DARK),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 7.5),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), COBALT_TINT),
            ("TEXTCOLOR", (0,-1), (-1,-1), COBALT),
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,1), (-1,-1), 8),
            ("LINEBELOW", (0,1), (-1,-2), 0.5, HAIRLINE),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, HAIRLINE]),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ])
        tb = data["total_sisa"]
        if tb < 0:
            ts.add("TEXTCOLOR", (3,-1), (3,-1), NEGATIVE)
        for ri in neg_rows:
            ts.add("TEXTCOLOR", (3,ri), (3,ri), NEGATIVE)
        st.setStyle(ts)
        elems += [st, Spacer(1, 0.5*cm)]

        # Budget detail
        elems.append(section_header("Detail Budget"))
        bgt_headers = ["Kategori 1", "Kategori 2", "Tanggal", "Pillar", "Amount (Rp)"]
        bgt_data = [wrap_row(bgt_headers, is_header=True)]
        bgt_total = 0
        for r in data["budget_rows"]:
            a = r.get("amount", 0); bgt_total += a
            bgt_data.append(wrap_row([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                             r.get("pillar",""), format_rupiah(a, prefix="")], amount_col=4))
        if data["budget_rows"]:
            bgt_data.append(wrap_row(["", "TOTAL", "", "", format_rupiah(bgt_total, prefix="")], is_footer=True))
        bt = Table(bgt_data, colWidths=[3.5*cm, 4*cm, 2.5*cm, 3*cm, 4*cm], repeatRows=1)
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), COBALT_TINT),
            ("TEXTCOLOR", (0,0), (-1,0), COBALT),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 7.5),
            ("LINEBELOW", (0,0), (-1,0), 1.2, COBALT),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), HAIRLINE),
            ("ALIGN", (4,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,1), (-1,-1), 8),
            ("LINEBELOW", (0,1), (-1,-2), 0.5, HAIRLINE),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, HAIRLINE]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        elems += [bt, Spacer(1, 0.5*cm)]

        # Payment detail
        elems.append(section_header("Detail Payment", accent=GREEN))
        pay_headers = ["Kategori 1", "Kategori 2", "Tanggal", "PAM", "Pillar", "Amount (Rp)", "Status", "Tanggal Bayar"]
        pay_data = [wrap_row(pay_headers, is_header=True)]
        pay_total = 0
        for r in data["payment_rows"]:
            a = r.get("amount", 0); pay_total += a
            pay_data.append(wrap_row([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                             r.get("pam",""), r.get("pillar",""),
                             format_rupiah(a, prefix=""), r.get("status",""),
                             r.get("tanggal_bayar","")], amount_col=5))
        if data["payment_rows"]:
            pay_data.append(wrap_row(["", "TOTAL", "", "", "", format_rupiah(pay_total, prefix=""), "", ""], is_footer=True))

        pt = Table(pay_data, colWidths=[2.4*cm, 2.4*cm, 2.1*cm, 2.4*cm, 1.5*cm, 2.3*cm, 1.5*cm, 2.1*cm], repeatRows=1)
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), GREEN_TINT),
            ("TEXTCOLOR", (0,0), (-1,0), GREEN),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 7.5),
            ("LINEBELOW", (0,0), (-1,0), 1.2, GREEN_LINE),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), HAIRLINE),
            ("ALIGN", (5,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,1), (-1,-1), 8),
            ("LINEBELOW", (0,1), (-1,-2), 0.5, HAIRLINE),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, HAIRLINE]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        elems.append(pt)

        def _draw_footer(canvas_obj, doc_obj):
            canvas_obj.saveState()
            canvas_obj.setFont("Helvetica", 7)
            canvas_obj.setFillColor(MUTED)
            canvas_obj.drawRightString(A4[0] - 1.5*cm, 1*cm, f"Halaman {doc_obj.page}")
            canvas_obj.restoreState()

        doc.build(elems, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf",
                         download_name=f"laporan_{code}.pdf", as_attachment=True)

    return ("Format tidak dikenal.", 400)


@bp.route("/rekap/data")
@jwt_html_required
@etf_company_required
def rekap_data():
    rows = get_rekap(_cid(),
        program=request.args.get("program", ""),
        pillar=request.args.get("pillar", ""),
        status=request.args.get("status", ""),
        search=request.args.get("search", ""),
        jenjang=request.args.get("jenjang", ""),
        angkatan=request.args.get("angkatan", ""))
    return jsonify({"ok": True, "rows": rows})


@bp.route("/rekap/export/xlsx")
@bp.route("/rekap/export/excel")
@jwt_html_required
@etf_company_required
def rekap_export_xlsx():
    from modules.beasiswa.exports import export_rekap_excel
    import io
    from flask import send_file
    from datetime import datetime

    program = request.args.get("program", "")
    pillar = request.args.get("pillar", "")
    status = request.args.get("status", "")
    search = request.args.get("search", "")
    jenjang = request.args.get("jenjang", "")
    angkatan = request.args.get("angkatan", "")

    xls_bytes = export_rekap_excel(
        _cid(),
        search=search,
        program=program,
        pillar=pillar,
        status=status,
        jenjang=jenjang,
        angkatan=angkatan,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Data_Siswa_Beasiswa_ETF_{timestamp}.xlsx"
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )


@bp.route("/rekap/export/csv")
@jwt_html_required
@etf_company_required
def rekap_export_csv():
    import csv, io
    rows  = get_rekap(_cid(),
        program=request.args.get("program", ""),
        pillar=request.args.get("pillar", ""),
        status=request.args.get("status", ""),
        search=request.args.get("search", ""),
        jenjang=request.args.get("jenjang", ""),
        angkatan=request.args.get("angkatan", ""))
    out   = io.StringIO()
    w     = csv.writer(out)
    w.writerow(["Code","Nama","Jenjang","Angkatan","Program","Status",
                "Total Budget","Total Payment","Sisa"])
    for r in rows:
        w.writerow([r["code"],r["nama"],r["jenjang"],r["angkatan"],r["program"],
                    r["status"],r["total_budget"],r["total_payment"],r["sisa"]])
    out.seek(0)
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=rekap_beasiswa.csv"})


@bp.route("/rekap/export/pdf")
@jwt_html_required
@etf_company_required
def rekap_export_pdf():
    import io
    from flask import send_file
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    rows   = get_rekap(_cid(),
        program=request.args.get("program", ""),
        pillar=request.args.get("pillar", ""),
        status=request.args.get("status", ""),
        search=request.args.get("search", ""),
        jenjang=request.args.get("jenjang", ""),
        angkatan=request.args.get("angkatan", ""))
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                               leftMargin=1.5*cm, rightMargin=1.5*cm,
                               topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles   = getSampleStyleSheet()
    elements = [
        Paragraph(f"Rekap Beasiswa — {session.get('company_name','')}", styles["Title"]),
        Spacer(1, 0.4*cm),
    ]
    header = [["No","Code","Nama","Jenjang","Program","Status","Budget","Payment","Sisa"]]
    for i, r in enumerate(rows, 1):
        fmt = lambda n: format_rupiah(n, prefix="")
        header.append([i, r["code"], r["nama"], r["jenjang"], r["program"],
                        r["status"], fmt(r["total_budget"]), fmt(r["total_payment"]), fmt(r["sisa"])])
    if rows:
        tb = sum(r["total_budget"] for r in rows)
        tp = sum(r["total_payment"] for r in rows)
        header.append(["","","TOTAL","","","", format_rupiah(tb, prefix=""), format_rupiah(tp, prefix=""), format_rupiah(tb-tp, prefix="")])

    tbl = Table(header, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#1a56db")),
        ("TEXTCOLOR",(0,0),(-1,0), colors.white),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 8),
        ("ALIGN",(6,0),(-1,-1), "RIGHT"),
        ("GRID",(0,0),(-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ("BACKGROUND",(0,-1),(-1,-1), colors.HexColor("#f3f4f6")),
        ("FONTNAME",(0,-1),(-1,-1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    elements.append(tbl)
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf",
                     download_name="rekap_beasiswa.pdf", as_attachment=True)


# --- Dashboard API Endpoints ---

@bp.route("/api/dashboard/summary")
@jwt_html_required
@etf_company_required
def api_dashboard_summary():
    years_str = request.args.get("years", "")
    pillars_str = request.args.get("pillars", "")
    years = [int(y) for y in years_str.split(",")] if years_str else []
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs_str = request.args.get("jenjangs", "")
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    angkatans_str = request.args.get("angkatans", "")
    angkatans = [a for a in angkatans_str.split(",") if a]
    statuses_str = request.args.get("statuses", "")
    statuses = [s for s in statuses_str.split(",") if s]
    return jsonify({"ok": True, "data": get_dashboard_summary(_cid(), years, pillars, programs, jenjangs, statuses, angkatans)})


@bp.route("/api/dashboard/breakdown")
@jwt_html_required
@etf_company_required
def api_dashboard_breakdown():
    years_str = request.args.get("years", "")
    pillars_str = request.args.get("pillars", "")
    years = [int(y) for y in years_str.split(",")] if years_str else []
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs_str = request.args.get("jenjangs", "")
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    angkatans_str = request.args.get("angkatans", "")
    angkatans = [a for a in angkatans_str.split(",") if a]
    statuses_str = request.args.get("statuses", "")
    statuses = [s for s in statuses_str.split(",") if s]
    return jsonify({"ok": True, "data": get_dashboard_breakdown(_cid(), years, pillars, programs, jenjangs, statuses, angkatans)})


@bp.route("/api/dashboard/monthly")
@jwt_html_required
@etf_company_required
def api_dashboard_monthly():
    years_str = request.args.get("years", "")
    pillars_str = request.args.get("pillars", "")
    years = [int(y) for y in years_str.split(",")] if years_str else []
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs_str = request.args.get("jenjangs", "")
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    angkatans_str = request.args.get("angkatans", "")
    angkatans = [a for a in angkatans_str.split(",") if a]
    statuses_str = request.args.get("statuses", "")
    statuses = [s for s in statuses_str.split(",") if s]
    return jsonify({"ok": True, "data": get_dashboard_monthly(_cid(), years, pillars, programs, jenjangs, statuses, angkatans)})


@bp.route("/api/dashboard/latest_payments")
@jwt_html_required
@etf_company_required
def api_dashboard_latest_payments():
    years_str = request.args.get("years", "")
    pillars_str = request.args.get("pillars", "")
    years = [int(y) for y in years_str.split(",")] if years_str else []
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs_str = request.args.get("jenjangs", "")
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    angkatans_str = request.args.get("angkatans", "")
    angkatans = [a for a in angkatans_str.split(",") if a]
    statuses_str = request.args.get("statuses", "")
    statuses = [s for s in statuses_str.split(",") if s]
    return jsonify({"ok": True, "data": get_dashboard_latest_payments(_cid(), years, pillars, programs, jenjangs, statuses, angkatans)})


@bp.route("/api/dashboard/program_summary")
@jwt_html_required
@etf_company_required
def api_dashboard_program_summary():
    years_str = request.args.get("years", "")
    pillars_str = request.args.get("pillars", "")
    years = [int(y) for y in years_str.split(",")] if years_str else []
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs_str = request.args.get("jenjangs", "")
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    angkatans_str = request.args.get("angkatans", "")
    angkatans = [a for a in angkatans_str.split(",") if a]
    statuses_str = request.args.get("statuses", "")
    statuses = [s for s in statuses_str.split(",") if s]
    return jsonify({"ok": True, "data": get_dashboard_program_summary(_cid(), years, pillars, programs, jenjangs, statuses, angkatans)})


@bp.route("/api/dashboard/pillar_yearly")
@jwt_html_required
@etf_company_required
def api_dashboard_pillar_yearly():
    pillars_str = request.args.get("pillars", "")
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs_str = request.args.get("jenjangs", "")
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    angkatans_str = request.args.get("angkatans", "")
    angkatans = [a for a in angkatans_str.split(",") if a]
    statuses_str = request.args.get("statuses", "")
    statuses = [s for s in statuses_str.split(",") if s]
    return jsonify({"ok": True, "data": get_dashboard_pillar_yearly(_cid(), pillars, programs, jenjangs, statuses, angkatans)})


@bp.route("/api/dashboard/export_trend_tahunan")
@jwt_html_required
@etf_company_required
def api_dashboard_export_trend_tahunan():
    from modules.beasiswa.exports import export_dashboard_trend_tahunan_excel
    import io
    from flask import send_file
    from datetime import datetime

    year_single = request.args.get("year", "").strip()
    years = [int(year_single)] if (year_single and year_single.isdigit()) else None

    pillars_str = request.args.get("pillars", "")
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs_str = request.args.get("jenjangs", "")
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    angkatans_str = request.args.get("angkatans", "")
    angkatans = [a for a in angkatans_str.split(",") if a]
    statuses_str = request.args.get("statuses", "")
    statuses = [s for s in statuses_str.split(",") if s]

    xls_bytes = export_dashboard_trend_tahunan_excel(
        _cid(),
        years=years,
        pillars=pillars,
        programs=programs,
        jenjangs=jenjangs,
        statuses=statuses,
        angkatans=angkatans,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if years and len(years) == 1:
        filename = f"Trend_Realisasi_Tahunan_ETF_{years[0]}_{timestamp}.xlsx"
    else:
        filename = f"Trend_Realisasi_Tahunan_ETF_{timestamp}.xlsx"

    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )



from modules.beasiswa.service import get_budget_requests, approve_budget_request_batch, reject_budget_request_batch


@bp.route("/approval-budget", methods=["GET"])
@jwt_html_required
@etf_company_required
def approval_budget_page():
    return render_template("beasiswa/approval.html", ctx=_ctx(), requests=get_budget_requests(_cid()))

@bp.route("/approval-budget/approve", methods=["POST"])
@role_required("BC", "Admin")
@etf_company_required
def approval_budget_approve():
    data = request.get_json(force=True) or {}
    req_ids = data.get("request_ids", [])
    if not req_ids:
        return jsonify({"ok": False, "pesan": "Tidak ada baris yang dipilih."})
    return jsonify(approve_budget_request_batch(_cid(), req_ids, _ctx()["current_user"]))

@bp.route("/approval-budget/reject", methods=["POST"])
@role_required("BC", "Admin")
@etf_company_required
def approval_budget_reject():
    data = request.get_json(force=True) or {}
    req_ids = data.get("request_ids", [])
    reason = data.get("reason", "").strip()
    if not req_ids:
        return jsonify({"ok": False, "pesan": "Tidak ada baris yang dipilih."})
    if not reason:
        return jsonify({"ok": False, "pesan": "Alasan penolakan wajib diisi."})
    return jsonify(reject_budget_request_batch(_cid(), req_ids, _ctx()["current_user"], reason))



