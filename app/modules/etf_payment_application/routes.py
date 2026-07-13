# modules/etf_payment_application/routes.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, Response
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.etf_payment_application.service import (
    get_pa_list, get_pa_flat, get_pa_header, bulk_update_pa, export_pa_excel,
    create_pa, update_pa, delete_pa, get_pa_lines, get_siswa_autocomplete,
    get_draft_siswa, get_draft_lines_for_siswa, get_pa_summary, VALID_TABS,
)
import config

bp = Blueprint("etf_payment_application", __name__, url_prefix="/etf-payment-application")


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


def _tab(allow_input: bool = False, allow_summary: bool = False, allow_advance: bool = False):
    t = request.args.get("tab", "summary").lower()
    if allow_input and t == "input":
        return "input"
    if allow_summary and t == "summary":
        return "summary"
    if allow_advance and t == "advance":
        return "advance"
    return t if t in VALID_TABS else "summary"


PA_PAGE_SIZE = 50


@bp.route("/")
@jwt_html_required
def index():
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))
    company_id = session["company_id"]
    tab = _tab(allow_input=True, allow_summary=True, allow_advance=True)
    sf = ""
    pa_rows = []
    all_rows = []
    page = 1
    total_pages = 1
    total_rows = 0
    start_row = 0
    end_row = 0
    f_nama = f_jenjang = f_program = f_angkatan = f_jenis = f_pam = f_bulan_pa = f_tahun_pa = ""
    if tab not in ("input", "summary", "advance"):
        sf = request.args.get("sf", "active").lower()
        if sf not in ("open", "on_process", "complete", "active", ""):
            sf = "active"
        all_rows = get_pa_flat(company_id, tab, sf)

        f_nama     = request.args.get("nama", "").strip()
        f_jenjang  = request.args.get("jenjang", "").strip()
        f_program  = request.args.get("program", "").strip()
        f_angkatan = request.args.get("angkatan", "").strip()
        f_jenis    = request.args.get("jenis", "").strip()
        f_pam      = request.args.get("pam", "").strip()
        f_bulan_pa = request.args.get("bulan_pa", "").strip()
        f_tahun_pa = request.args.get("tahun_pa", "").strip()
        nama_lc = f_nama.lower()
        pam_lc = f_pam.lower()

        # Filtered in Python (not SQL) so `all_rows` above stays the full,
        # unfiltered per-tab/status set the dropdown option lists are built
        # from below — otherwise typing a name would shrink the other
        # filter dropdowns' available choices too.
        filtered_rows = [
            r for r in all_rows
            if (not nama_lc or nama_lc in (r.get("nama") or "").lower())
            and (not f_jenjang or (r.get("jenjang_pendidikan") or "") == f_jenjang)
            and (not f_program or (r.get("program_beasiswa") or "") == f_program)
            and (not f_angkatan or str(r.get("angkatan_etf") or "") == f_angkatan)
            and (not f_jenis or (r.get("jenis_pembayaran") or "") == f_jenis)
            and (not pam_lc or pam_lc in (r.get("nomor_pam") or "").lower())
            and (not f_bulan_pa or (r.get("tgl_payment_application") or "")[5:7] == f_bulan_pa)
            and (not f_tahun_pa or (r.get("tgl_payment_application") or "")[0:4] == f_tahun_pa)
        ]

        total_rows = len(filtered_rows)
        try:
            page = int(request.args.get("page", 1))
        except ValueError:
            page = 1
        total_pages = max(1, -(-total_rows // PA_PAGE_SIZE))
        page = min(max(1, page), total_pages)
        offset = (page - 1) * PA_PAGE_SIZE
        pa_rows = filtered_rows[offset:offset + PA_PAGE_SIZE]
        start_row = offset + 1 if total_rows else 0
        end_row = min(offset + PA_PAGE_SIZE, total_rows)
    return render_template(
        "etf_payment_application/index.html",
        pa_rows=pa_rows,
        all_pa_rows=all_rows,
        active_tab=tab,
        active_sf=sf,
        page=page,
        page_size=PA_PAGE_SIZE,
        total_pages=total_pages,
        total_rows=total_rows,
        start_row=start_row,
        end_row=end_row,
        f_nama=f_nama,
        f_jenjang=f_jenjang,
        f_program=f_program,
        f_angkatan=f_angkatan,
        f_jenis=f_jenis,
        f_pam=f_pam,
        f_bulan_pa=f_bulan_pa,
        f_tahun_pa=f_tahun_pa,
        cat1=config.CAT1_BGT,
        cat2_sem=config.CAT2_SEM,
        active_page="etf_payment_app",
        jenjang=config.JENJANG,
        program=config.PROGRAM,
        status_siswa=config.STATUS_SISWA,
        **_ctx(),
    )


@bp.route("/siswa-search")
@jwt_html_required
def siswa_search():
    q          = request.args.get("q", "")
    company_id = session.get("company_id")
    return jsonify(get_siswa_autocomplete(company_id, q))


@bp.route("/draft-siswa")
@jwt_html_required
def draft_siswa():
    q          = request.args.get("q", "")
    company_id = session.get("company_id")
    return jsonify(get_draft_siswa(company_id, q, _tab()))


@bp.route("/draft-lines")
@jwt_html_required
def draft_lines():
    siswa_id   = request.args.get("siswa_id", type=int)
    company_id = session.get("company_id")
    if not siswa_id:
        return jsonify([])
    return jsonify(get_draft_lines_for_siswa(company_id, siswa_id, _tab()))


@bp.route("/create", methods=["POST"])
@jwt_html_required
def create():
    company_id = session.get("company_id")
    tab        = request.args.get("tab", "agri").lower()
    if tab not in VALID_TABS:
        tab = "agri"
    data   = request.get_json(force=True)
    header = {
        "tgl_payment_application": data.get("tgl_payment_application", ""),
        "tgl_surat_pengajuan":     data.get("tgl_surat_pengajuan", ""),
        "keterangan":              data.get("keterangan", ""),
        "doc_received_by_educ":    data.get("doc_received_by_educ", ""),
        "received_pa_from_educ":   data.get("received_pa_from_educ", ""),
    }
    lines = data.get("lines", [])
    route = (data.get("route") or "gl").lower()
    if route not in ("gl", "advance"):
        route = "gl"
    return jsonify(create_pa(company_id, header, lines, tab, route=route))


@bp.route("/<int:pa_id>/update", methods=["POST"])
@jwt_html_required
def update(pa_id):
    company_id = session.get("company_id")
    tab        = request.args.get("tab", "agri").lower()
    if tab not in VALID_TABS:
        tab = "agri"
    data = request.get_json(force=True)
    return jsonify(update_pa(pa_id, company_id, data, tab))


@bp.route("/<int:pa_id>/delete", methods=["POST"])
@jwt_html_required
def delete(pa_id):
    company_id = session.get("company_id")
    tab        = request.args.get("tab", "agri").lower()
    if tab not in VALID_TABS:
        tab = "agri"
    return jsonify(delete_pa(pa_id, company_id, tab))


@bp.route("/<int:pa_id>/lines")
@jwt_html_required
def lines(pa_id):
    company_id = session.get("company_id")
    return jsonify(get_pa_lines(pa_id, company_id, _tab()))


@bp.route("/export-excel")
@jwt_html_required
def export_excel():
    company_id = session.get("company_id")
    tab      = _tab()
    sf       = request.args.get("sf",       "").strip()
    nama     = request.args.get("nama",     "").strip()
    jenjang  = request.args.get("jenjang",  "").strip()
    program  = request.args.get("program",  "").strip()
    angkatan = request.args.get("angkatan", "").strip()
    jenis    = request.args.get("jenis",    "").strip()
    pam      = request.args.get("pam",      "").strip()
    bulan_pa = request.args.get("bulan_pa", "").strip()
    tahun_pa = request.args.get("tahun_pa", "").strip()
    data = export_pa_excel(company_id, tab, sf, nama, jenjang, program, angkatan, jenis, pam, bulan_pa, tahun_pa)
    from datetime import datetime
    fname = f"{tab.upper()}_PA_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return Response(
        data,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"}
    )


@bp.route("/bulk-update", methods=["POST"])
@jwt_html_required
def bulk_update():
    company_id = session.get("company_id")
    tab        = request.args.get("tab", "agri").lower()
    if tab not in VALID_TABS:
        tab = "agri"
    data = request.get_json(force=True)
    return jsonify(bulk_update_pa(
        data.get("pa_ids", []),
        data.get("field", ""),
        data.get("value", ""),
        company_id,
        tab,
    ))


@bp.route("/<int:pa_id>/header")
@jwt_html_required
def header(pa_id):
    company_id = session.get("company_id")
    data = get_pa_header(pa_id, company_id, _tab())
    if not data:
        return jsonify({"ok": False}), 404
    return jsonify(data)


@bp.route("/summary-data")
@jwt_html_required
def summary_data():
    company_id = session.get("company_id")
    all_data = []
    for t in VALID_TABS:
        rows = get_pa_flat(company_id, tab=t)
        for r in rows:
            r['nama_student'] = r.get('nama', '')
            r['pillar'] = t
            all_data.append(r)
    # Urutkan berdasarkan pa_number descending
    all_data.sort(key=lambda x: x.get('pa_number', ''), reverse=True)
    return jsonify(all_data)


@bp.route("/advance-data")
@jwt_html_required
def advance_data():
    company_id = session.get("company_id")
    status     = request.args.get("status", "").strip().lower()
    all_data   = []
    for t in VALID_TABS:
        rows = get_pa_flat(company_id, tab=t)
        for r in rows:
            # Filter on the PA header's own route (source of truth), not the
            # denormalized per-line copy — the header is authoritative per design.
            if (r.get("pa_route") or "gl") != "advance":
                continue
            if status and (r.get("status") or "").lower() != status:
                continue
            r['nama_student'] = r.get('nama', '')
            r['pillar'] = t
            all_data.append(r)
    all_data.sort(key=lambda x: x.get('pa_number', ''), reverse=True)
    return jsonify(all_data)
