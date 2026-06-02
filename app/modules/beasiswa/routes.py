# modules/beasiswa/routes.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, Response
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required, role_required
from modules.beasiswa.service import (
    generate_kode_siswa, get_siswa_list, get_siswa_detail,
    add_siswa, update_siswa, update_siswa_catatan, update_siswa_catatan_payment, delete_siswa,
    add_budget_batch, get_budget, delete_budget_row, update_budget_row,
    add_payment_batch, add_payment_multi, get_payment, get_payment_list, delete_payment_row,
    get_sisa_budget, get_rekap, get_budget_list, get_laporan_siswa,
    get_financial_summary,
    add_klaim_multi, get_klaim_list, delete_klaim_row,
    get_vendors,
)
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


@bp.route("/")
@jwt_html_required
def index():
    if not _cid():
        return redirect(url_for("dashboard.select_company"))
    return render_template(
        "beasiswa/index.html",
        siswa_list=get_siswa_list(_cid()),
        jenjang=config.JENJANG,
        program=config.PROGRAM,
        status_siswa=config.STATUS_SISWA,
        pillar=config.PILLAR,
        cat1_bgt=config.CAT1_BGT,
        cat2_sem=config.CAT2_SEM,
        perusahaan=config.PERUSAHAAN,
        vendor_list=get_vendors(),
        active_page="beasiswa",
        **_ctx()
    )


@bp.route("/siswa/generate-kode")
@role_required("requester", "verificator", "releaser")
def siswa_generate_kode():
    jenjang  = request.args.get("jenjang", "").strip()
    angkatan = request.args.get("angkatan", "").strip()
    if not jenjang or not angkatan.isdigit() or len(angkatan) != 4:
        return jsonify({"ok": False, "pesan": "Jenjang dan angkatan (4 digit) wajib diisi."})
    kode = generate_kode_siswa(jenjang, int(angkatan), _cid())
    return jsonify({"ok": True, "kode": kode})


@bp.route("/siswa/tambah", methods=["POST"])
@role_required("requester", "verificator", "releaser")
def siswa_tambah():
    return jsonify(add_siswa(_cid(), request.get_json(force=True) or {}))


@bp.route("/siswa/<code>")
@role_required("requester", "verificator", "releaser")
def siswa_detail(code):
    row = get_siswa_detail(_cid(), code)
    if not row:
        return jsonify({"ok": False, "pesan": "Tidak ditemukan."})
    return jsonify({"ok": True, "data": row})


@bp.route("/siswa/<code>/update", methods=["POST"])
@role_required("requester", "verificator", "releaser")
def siswa_update(code):
    return jsonify(update_siswa(_cid(), code, request.get_json(force=True) or {}))


@bp.route("/siswa/<code>/catatan", methods=["POST"])
@role_required("requester", "verificator", "releaser")
def siswa_catatan_update(code):
    data = request.get_json(force=True) or {}
    return jsonify(update_siswa_catatan(_cid(), code, data.get("catatan", "")))


@bp.route("/siswa/<code>/catatan-payment", methods=["POST"])
@role_required("requester", "verificator", "releaser")
def siswa_catatan_payment_update(code):
    data = request.get_json(force=True) or {}
    return jsonify(update_siswa_catatan_payment(_cid(), code, data.get("catatan_payment", "")))


@bp.route("/siswa/<code>/hapus", methods=["POST"])
@role_required("requester", "verificator", "releaser")
def siswa_hapus(code):
    return jsonify(delete_siswa(_cid(), code))


@bp.route("/siswa/<code>/sisa-budget")
@role_required("requester", "verificator", "releaser")
def siswa_sisa_budget(code):
    sisa = get_sisa_budget(_cid(), code)
    return jsonify({"ok": True, **sisa})


@bp.route("/budget/siswa/<code>")
@role_required("requester", "verificator", "releaser")
def budget_by_siswa(code):
    result = get_budget(_cid(), code)
    siswa  = get_siswa_detail(_cid(), code)
    return jsonify({"ok": True, "nama": siswa["nama"] if siswa else "",
                    "catatan_budget": (siswa["catatan_budget"] or "") if siswa else "", **result})


@bp.route("/budget/siswa/<code>/export/<fmt>")
@role_required("requester", "verificator", "releaser")
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
                         r.get("pillar",""), f"{r.get('amount',0):,.0f}"])
        if rows:
            data.append(["", "TOTAL", "", "", "", f"{grand:,.0f}"])
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
@role_required("requester", "verificator", "releaser")
def budget_hapus(row_id):
    return jsonify(delete_budget_row(_cid(), row_id))


@bp.route("/budget/<int:row_id>/update", methods=["POST"])
@role_required("requester", "verificator", "releaser")
def budget_update_row(row_id):
    return jsonify(update_budget_row(_cid(), row_id, request.get_json(force=True) or {}))


@bp.route("/budget/tambah", methods=["POST"])
@role_required("requester", "verificator", "releaser")
def budget_tambah():
    data   = request.get_json(force=True) or {}
    code   = (data.get("code") or "").strip()
    if not code:
        return jsonify({"ok": False, "pesan": "Code siswa wajib diisi."})
    return jsonify(add_budget_batch(_cid(), code,
        data.get("tanggal", ""), data.get("pillar", ""), data.get("items", [])))


@bp.route("/vendors")
@role_required("requester", "verificator", "releaser")
def vendor_list_api():
    search = request.args.get("search", "").strip()
    return jsonify({"ok": True, "rows": get_vendors(search)})


@bp.route("/summary")
@role_required("requester", "verificator", "releaser")
def financial_summary():
    return jsonify({"ok": True, **get_financial_summary(_cid())})


@bp.route("/budget/list")
@role_required("requester", "verificator", "releaser")
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


@bp.route("/budget/export/csv")
@role_required("requester", "verificator", "releaser")
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
@role_required("requester", "verificator", "releaser")
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
                     r.get("pillar",""), f"{a:,.0f}"])
    if rows:
        data.append(["","","TOTAL","","","","","",f"{total:,.0f}"])
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
@role_required("requester", "verificator", "releaser")
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


@bp.route("/payment/export/csv")
@role_required("requester", "verificator", "releaser")
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
@role_required("requester", "verificator", "releaser")
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
                     r.get("pillar",""), f"{a:,.0f}",
                     r.get("pam",""), r.get("perusahaan",""), r.get("status","")])
    if rows:
        data.append(["","","TOTAL","","","","","",f"{total:,.0f}","","",""])
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
@role_required("requester", "verificator", "releaser")
def payment_hapus(row_id):
    return jsonify(delete_payment_row(_cid(), row_id))


@bp.route("/payment/tambah", methods=["POST"])
@role_required("requester", "verificator", "releaser")
def payment_tambah():
    data   = request.get_json(force=True) or {}
    code   = (data.get("code") or "").strip()
    if not code:
        return jsonify({"ok": False, "pesan": "Code siswa wajib diisi."})
    return jsonify(add_payment_batch(_cid(), code,
        data.get("tanggal", ""), data.get("pillar", ""),
        data.get("perusahaan", ""), data.get("items", [])))


@bp.route("/payment/tambah-multi", methods=["POST"])
@role_required("requester", "verificator", "releaser")
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
@role_required("requester", "verificator", "releaser")
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
@role_required("requester", "verificator", "releaser")
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
@role_required("requester", "verificator", "releaser")
def klaim_hapus(row_id):
    return jsonify(delete_klaim_row(_cid(), row_id))


@bp.route("/laporan/siswa/<code>")
@role_required("requester", "verificator", "releaser")
def laporan_siswa(code):
    data = get_laporan_siswa(_cid(), code)
    if not data:
        return jsonify({"ok": False, "pesan": "Siswa tidak ditemukan."})
    return jsonify({"ok": True, **data})


@bp.route("/laporan/siswa/<code>/export/<fmt>")
@role_required("requester", "verificator", "releaser")
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
        elems = [Paragraph(f"Laporan Siswa — {s.get('nama','')} ({s.get('code','')})", styles["Title"]),
                 Paragraph(session.get("company_name", ""), styles["Normal"]),
                 Spacer(1, 0.4*cm)]

        # Student info table (2-column label/value pairs)
        elems.append(Paragraph("Data Siswa", styles["Heading2"]))
        info_rows = [
            ["Kode Siswa", s.get("code",""),          "Status", s.get("status","")],
            ["Nama",       s.get("nama",""),           "Program", s.get("program","")],
            ["Jenjang",    s.get("jenjang",""),        "Angkatan", str(s.get("angkatan",""))],
            ["Universitas",s.get("universitas",""),    "Fakultas", s.get("fakultas","")],
            ["Bank",       s.get("bank",""),           "No. Rekening", s.get("norek","")],
            ["Nama Rek.",  s.get("namarek",""),        "Referensi", s.get("referensi","")],
        ]
        if s.get("catatan"):
            info_rows.append(["Catatan", s.get("catatan",""), "", ""])
        info_tbl = Table(info_rows, colWidths=[2.5*cm, 5.5*cm, 2.5*cm, 6.5*cm])
        info_tbl.setStyle(TableStyle([
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTNAME",   (2,0), (2,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#f3f4f6")),
            ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#f3f4f6")),
            ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        elems += [info_tbl, Spacer(1, 0.3*cm)]

        # IPK section
        ipk_sems = [(i, s.get(f"ipk_sem{i}")) for i in range(1,11) if s.get(f"ipk_sem{i}")]
        ipk_pens = [(i, s.get(f"ipk_pen{i}")) for i in range(1,4) if s.get(f"ipk_pen{i}")]
        if ipk_sems or ipk_pens:
            elems.append(Paragraph("IPK", styles["Heading2"]))
            ipk_rows = []
            if ipk_sems:
                ipk_rows.append(["IPK Semester"] + [f"Sem {i}: {float(v):.2f}" for i, v in ipk_sems])
            if ipk_pens:
                ipk_rows.append(["IPK Penelitian"] + [f"Tahap {i}: {float(v):.2f}" for i, v in ipk_pens])
            max_cols = max(len(r) for r in ipk_rows)
            for r in ipk_rows:
                while len(r) < max_cols:
                    r.append("")
            ipk_tbl = Table(ipk_rows)
            ipk_tbl.setStyle(TableStyle([
                ("FONTSIZE",   (0,0), (-1,-1), 8),
                ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
                ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#f3f4f6")),
                ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
                ("TOPPADDING", (0,0), (-1,-1), 3),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ]))
            elems += [ipk_tbl, Spacer(1, 0.3*cm)]

        # Summary table
        elems.append(Paragraph("Rekapitulasi per Kategori", styles["Heading2"]))
        sum_data = [["Kategori", "Budget (Rp)", "Payment (Rp)", "Selisih (Rp)"]]
        for c in data["cat_summary"]:
            sum_data.append([c["cat1"], f"{c['budget']:,.0f}", f"{c['payment']:,.0f}", f"{c['sisa']:,.0f}"])
        sum_data.append(["TOTAL", f"{data['total_budget']:,.0f}",
                         f"{data['total_payment']:,.0f}", f"{data['total_sisa']:,.0f}"])
        st = Table(sum_data, colWidths=[5*cm, 4*cm, 4*cm, 4*cm])
        neg_rows = [i+1 for i, c in enumerate(data["cat_summary"]) if c["sisa"] < 0]
        ts = TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a56db")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ])
        tb = data["total_sisa"]
        if tb < 0:
            ts.add("TEXTCOLOR", (3,-1), (3,-1), colors.HexColor("#dc2626"))
        for ri in neg_rows:
            ts.add("TEXTCOLOR", (3,ri), (3,ri), colors.HexColor("#dc2626"))
        st.setStyle(ts)
        elems += [st, Spacer(1, 0.4*cm)]

        # Budget detail
        elems.append(Paragraph("Detail Budget", styles["Heading2"]))
        bgt_data = [["Kategori 1", "Kategori 2", "Tanggal", "Pillar", "Amount (Rp)"]]
        bgt_total = 0
        for r in data["budget_rows"]:
            a = r.get("amount", 0); bgt_total += a
            bgt_data.append([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                             r.get("pillar",""), f"{a:,.0f}"])
        if data["budget_rows"]:
            bgt_data.append(["", "TOTAL", "", "", f"{bgt_total:,.0f}"])
        bt = Table(bgt_data, colWidths=[3.5*cm, 4*cm, 2.5*cm, 3*cm, 4*cm], repeatRows=1)
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a56db")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
            ("ALIGN", (4,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        elems += [bt, Spacer(1, 0.4*cm)]

        # Payment detail
        elems.append(Paragraph("Detail Payment", styles["Heading2"]))
        pay_data = [["Kategori 1", "Kategori 2", "Tanggal", "PAM", "Perusahaan", "Pillar", "Amount (Rp)", "Status"]]
        pay_total = 0
        for r in data["payment_rows"]:
            a = r.get("amount", 0); pay_total += a
            pay_data.append([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                             r.get("pam",""), r.get("perusahaan",""), r.get("pillar",""),
                             f"{a:,.0f}", r.get("status","")])
        if data["payment_rows"]:
            pay_data.append(["", "TOTAL", "", "", "", "", f"{pay_total:,.0f}", ""])
        pt = Table(pay_data, colWidths=[2.5*cm, 2.5*cm, 2.0*cm, 2.0*cm, 2.5*cm, 2.0*cm, 2.5*cm, 1.8*cm], repeatRows=1)
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#065f46")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
            ("ALIGN", (6,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        elems.append(pt)

        doc.build(elems)
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf",
                         download_name=f"laporan_{code}.pdf", as_attachment=True)

    return ("Format tidak dikenal.", 400)


@bp.route("/rekap/data")
@role_required("requester", "verificator", "releaser")
def rekap_data():
    rows = get_rekap(_cid(),
        program=request.args.get("program", ""),
        pillar=request.args.get("pillar", ""),
        status=request.args.get("status", ""),
        search=request.args.get("search", ""),
        jenjang=request.args.get("jenjang", ""),
        angkatan=request.args.get("angkatan", ""))
    return jsonify({"ok": True, "rows": rows})


@bp.route("/rekap/export/csv")
@role_required("requester", "verificator", "releaser")
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
@role_required("requester", "verificator", "releaser")
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
        fmt = lambda n: f"{n:,.0f}"
        header.append([i, r["code"], r["nama"], r["jenjang"], r["program"],
                        r["status"], fmt(r["total_budget"]), fmt(r["total_payment"]), fmt(r["sisa"])])
    if rows:
        tb = sum(r["total_budget"] for r in rows)
        tp = sum(r["total_payment"] for r in rows)
        header.append(["","","TOTAL","","","", f"{tb:,.0f}", f"{tp:,.0f}", f"{tb-tp:,.0f}"])

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
