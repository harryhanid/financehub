# modules/beasiswa/routes.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, Response
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required, role_required
from modules.beasiswa.service import (
    generate_kode_siswa, get_siswa_list, get_siswa_detail,
    add_siswa, update_siswa, add_budget_batch, get_budget,
    add_payment_batch, get_payment, get_sisa_budget, get_rekap
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
@role_required("requester", "verificator")
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
@role_required("requester", "verificator")
def siswa_update(code):
    return jsonify(update_siswa(_cid(), code, request.get_json(force=True) or {}))


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
    return jsonify({"ok": True, "nama": siswa["nama"] if siswa else "", **result})


@bp.route("/budget/tambah", methods=["POST"])
@role_required("requester", "verificator")
def budget_tambah():
    data   = request.get_json(force=True) or {}
    code   = (data.get("code") or "").strip()
    if not code:
        return jsonify({"ok": False, "pesan": "Code siswa wajib diisi."})
    return jsonify(add_budget_batch(_cid(), code,
        data.get("tanggal", ""), data.get("pillar", ""), data.get("items", [])))


@bp.route("/payment/tambah", methods=["POST"])
@role_required("requester")
def payment_tambah():
    data   = request.get_json(force=True) or {}
    code   = (data.get("code") or "").strip()
    if not code:
        return jsonify({"ok": False, "pesan": "Code siswa wajib diisi."})
    return jsonify(add_payment_batch(_cid(), code,
        data.get("tanggal", ""), data.get("pillar", ""),
        data.get("perusahaan", ""), data.get("items", [])))


@bp.route("/rekap/data")
@role_required("requester", "verificator", "releaser")
def rekap_data():
    rows = get_rekap(_cid(),
        program=request.args.get("program", ""),
        pillar=request.args.get("pillar", ""),
        status=request.args.get("status", ""))
    return jsonify({"ok": True, "rows": rows})


@bp.route("/rekap/export/csv")
@role_required("requester", "verificator", "releaser")
def rekap_export_csv():
    import csv, io
    rows  = get_rekap(_cid(),
        program=request.args.get("program", ""),
        pillar=request.args.get("pillar", ""),
        status=request.args.get("status", ""))
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
        status=request.args.get("status", ""))
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
