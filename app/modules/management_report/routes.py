# modules/management_report/routes.py
import io
from datetime import date

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for, Response
from flask_jwt_extended import get_jwt

import config
from auth.middleware import is_admin, json_admin_required, jwt_html_required
from modules.management_report import bgt_report, exports, ho_report, service
from modules.management_report import sync as mr_sync
from modules.management_report.formatting import id_amount, id_number, id_percent
from modules.management_report.ho_template import load_template
from modules.management_report.parser import ParseError, read_append1, read_meta

bp = Blueprint("management_report", __name__, url_prefix="/management-report")

# Indonesian number style (1.234,5) in this module's templates
bp.add_app_template_filter(id_number, "mr_num")
bp.add_app_template_filter(id_percent, "mr_pct")
bp.add_app_template_filter(id_amount, "mr_amt")


def _ctx():
    try:
        claims = get_jwt()
        return {
            "current_user": claims.get("username", ""),
            "current_role": claims.get("role", ""),
            "can_manage":   is_admin(claims),
            "company_id":   session.get("company_id"),
            "company_code": session.get("company_code"),
            "company_name": session.get("company_name"),
        }
    except Exception:
        return {}


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _filters() -> dict:
    return {
        "cc": request.args.get("cc") or None,
        "yy": _to_int(request.args.get("yy")),
        "mm": _to_int(request.args.get("mm")),
        "coas": [c for c in request.args.getlist("coa") if c],
        "cats": [c for c in request.args.getlist("cat") if c],
    }


ALL_CC = "ALL"                    # value of the "All Cost Center" option in the CC filter
ALL_CC_LABEL = "All Cost Center"


def _resolve(company_id):
    """Filters from the query string, with the CC resolved against the active snapshot."""
    f = _filters()
    options = service.get_filter_options(company_id)
    if f["cc"] == ALL_CC or f["cc"] in options["ccs"]:
        cc = f["cc"]
    else:
        cc = options["ccs"][0] if options["ccs"] else None
    return options, {**f, "cc": cc}


def _report_title(cc, meta) -> str:
    """'<organisation> – <CC description>'; cc=None (All Cost Center) gives '... – All'."""
    desc = "All" if cc is None else (meta["cc_names"].get(cc) or cc)
    return f"{load_template()['org']} – {desc}"


def _ho_for(company_id, filters):
    cc = filters["cc"]
    real = None if cc in (None, ALL_CC) else cc
    return ho_report.build_ho_report(company_id, real, filters["yy"], filters["mm"],
                                     filters["coas"], filters["cats"])


def _company_code(company_id) -> str:
    return next((c["code"] for c in config.COMPANIES if c["id"] == company_id), "")


def _has_lines_up_to(rows, mm) -> bool:
    """True when any line falls in the Period (year to date); every line counts when mm is None."""
    return any(mm is None or (r.get("mm") or 0) <= mm for r in rows)


def _bgt_for(company_id, real_cc, filters, title, meta):
    """Sheet 1 data: lines of the year (no month filter) so full-year and YTD columns can both be filled."""
    rows = service.query_append(company_id, real_cc, filters["yy"], None, filters["coas"], cats=filters["cats"])["rows"]
    bgt = bgt_report.build_bgt_report(rows, filters["yy"], filters["mm"], meta.get("period"))
    code = real_cc or "All"
    cc_names = meta.get("cc_names") or {}
    bgt.update(title=title, cc_code=code, cc_desc=(cc_names.get(code) or code) if real_cc else "All",
               company_code=_company_code(company_id), has_rows=_has_lines_up_to(rows, filters["mm"]))
    return bgt


def _screen_bgt(company_id, filters):
    """The on-screen Report tab = sheet 1: the same data as the export; None when there is no CC to show."""
    cc = filters["cc"]
    if cc is None:
        return None
    real = None if cc == ALL_CC else cc
    meta = service.get_active_meta(company_id)
    return _bgt_for(company_id, real, filters, _report_title(real, meta), meta)


@bp.route("/table")
@jwt_html_required
def table():
    """Only the Report table; the page fetches it whenever a filter changes."""
    company_id = session.get("company_id")
    if not company_id:
        return "", 400
    _, filters = _resolve(company_id)
    return render_template("management_report/_report_table.html",
                           bgt=_screen_bgt(company_id, filters))


@bp.route("/ho-table")
@jwt_html_required
def ho_table():
    """Only the HO Report; it follows the same CC/YY/MM/COA/Category filters as the Report."""
    company_id = session.get("company_id")
    if not company_id:
        return "", 400
    _, filters = _resolve(company_id)
    return render_template("management_report/_ho_table.html", ho=_ho_for(company_id, filters))


APPEND_PAGE_SIZE = 100


def _append_args(company_id):
    """cc, q, page for the Data Sync table; an unknown or ALL cc means all cost centers."""
    cc = request.args.get("cc") or None
    if cc not in service.get_filter_options(company_id)["ccs"]:
        cc = None
    q = (request.args.get("q") or "").strip()[:100]
    page = min(max(1, _to_int(request.args.get("page")) or 1), 10 ** 6)   # keeps the OFFSET inside SQLite's integer range
    return cc, q, page


@bp.route("/append-table")
@jwt_html_required
def append_table():
    """One page of the Append table (Data Sync tab); the page refetches it on every filter change."""
    company_id = session.get("company_id")
    if not company_id:
        return "", 400
    cc, q, page = _append_args(company_id)
    res = service.query_append(company_id, cc, q=q, limit=APPEND_PAGE_SIZE,
                               offset=(page - 1) * APPEND_PAGE_SIZE)
    pages = max(1, -(-res["total"] // APPEND_PAGE_SIZE))
    if page > pages:
        page = pages
        res = service.query_append(company_id, cc, q=q, limit=APPEND_PAGE_SIZE,
                                   offset=(page - 1) * APPEND_PAGE_SIZE)
    return render_template("management_report/_append_table.html",
                           rows=res["rows"], total=res["total"], page=page, pages=pages,
                           has_snapshot=service.get_active_upload_id(company_id) is not None)


@bp.route("/append/export")
@jwt_html_required
def append_export():
    """Everything that passes the Data Sync table's CC and search filters, as one xlsx."""
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Pilih perusahaan terlebih dahulu."}), 400
    cc, q, _ = _append_args(company_id)
    rows = service.query_append(company_id, cc, q=q)["rows"]
    if not rows:
        return jsonify({"ok": False, "pesan": "Tidak ada data Append untuk diexport."}), 404
    return _attachment(exports.build_append_workbook(rows), "Append.xlsx", _XLSX)


@bp.route("/")
@jwt_html_required
def index():
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))
    company_id = session["company_id"]
    options, filters = _resolve(company_id)
    return render_template(
        "management_report/index.html",
        options=options, filters=filters,
        bgt=_screen_bgt(company_id, filters),
        ho=_ho_for(company_id, filters),
        default_tab="report" if options["ccs"] else "sync",
        uploads=service.list_uploads(company_id),
        last_summary=service.get_active_summary(company_id),
        active_page="management_report",
        use_unified_header=True,                      # module switcher + the tab bar (module_tabs block)
        **_ctx(),
    )


@bp.route("/sync", methods=["POST"])
@json_admin_required
def sync_excel():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Pilih perusahaan terlebih dahulu."}), 400
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "pesan": "File belum dipilih."}), 400
    if not f.filename.lower().endswith(".xlsb"):
        return jsonify({"ok": False, "pesan": "File harus berformat .xlsb."}), 400
    data = f.read()
    try:
        result = read_append1(io.BytesIO(data))
        if not result.rows:
            raise ParseError("Tidak ada baris data yang valid di sheet Append1.")
    except ParseError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    meta = read_meta(io.BytesIO(data))
    out = mr_sync.sync_rows(company_id, f.filename, get_jwt().get("username", ""), result.rows,
                            meta=meta)
    if not out["changed"]:
        pesan = (f"Sudah sinkron: tidak ada perubahan sejak sync terakhir "
                 f"({out['rows']} baris).")
    else:
        s = out["summary"]
        pesan = (f"Sync selesai: {s['rows_before']} → {s['rows_after']} baris "
                 f"({result.dropped} baris dilewati).")
        if s.get("meta_changed"):
            pesan += " Deskripsi CC / periode laporan diperbarui."
    return jsonify({"ok": True, "dropped": result.dropped, "pesan": pesan, **out})


@bp.route("/uploads/<int:upload_id>/activate", methods=["POST"])
@json_admin_required
def activate(upload_id):
    company_id = session.get("company_id")
    if not company_id or not service.activate_upload(company_id, upload_id):
        return jsonify({"ok": False, "pesan": "Snapshot tidak ditemukan atau sudah dihapus."}), 404
    return jsonify({"ok": True, "pesan": "Snapshot diaktifkan."})


_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _attachment(data: bytes, filename: str, mimetype: str):
    return Response(data, mimetype=mimetype,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def _sheets() -> str:
    """Sheets to export: '1', '12' or '123' (default; the legacy append=0 means '12')."""
    value = request.args.get("sheets")
    if value in ("1", "12", "123"):
        return value
    return "12" if request.args.get("append") == "0" else "123"


@bp.route("/export")
@jwt_html_required
def export_one():
    company_id = session.get("company_id")
    f = _filters()
    if not company_id or not f["cc"]:
        return jsonify({"ok": False, "pesan": "CC belum dipilih."}), 400
    real = None if f["cc"] == ALL_CC else f["cc"]
    report = service.build_report(company_id, real, f["yy"], f["mm"], f["coas"], f["cats"])
    meta = service.get_active_meta(company_id)
    report["title"] = _report_title(real, meta)
    if real is None:
        report["cc"] = ALL_CC_LABEL
    bgt = _bgt_for(company_id, real, f, report["title"], meta)
    # the month filter is the Period (year to date), so lines up to that month still export
    if not report["has_data"] and not bgt["has_rows"]:
        return jsonify({"ok": False, "pesan": "Tidak ada data untuk CC dan filter ini."}), 404
    sheets = _sheets()
    ho = ho_report.build_ho_report(company_id, real, f["yy"], f["mm"], f["coas"], f["cats"]) if "2" in sheets else None
    append_rows = (service.query_append(company_id, real, f["yy"], f["mm"], f["coas"], cats=f["cats"])["rows"]
                   if "3" in sheets else None)
    data = exports.build_cc_workbook(report, f, ho, append_rows, bgt)
    return _attachment(data, f"{exports.safe_filename(f['cc'])}.xlsx", _XLSX)


@bp.route("/export-all")
@jwt_html_required
def export_all():
    company_id = session.get("company_id")
    f = _filters()
    if not company_id:
        return jsonify({"ok": False, "pesan": "Pilih perusahaan terlebih dahulu."}), 400
    sheets = _sheets()
    meta = service.get_active_meta(company_id)
    reports, ho_by_cc, append_by_cc, bgt_by_cc = [], {}, {}, {}
    # every CC with data in the year; like export_one, one qualifies when it has data in the month
    # or lines up to that month (the month filter is the Period, year to date)
    for cc in service.list_ccs_with_data(company_id, f["yy"], None, f["coas"], f["cats"]):
        report = service.build_report(company_id, cc, f["yy"], f["mm"], f["coas"], f["cats"])
        report["title"] = _report_title(cc, meta)
        bgt = _bgt_for(company_id, cc, f, report["title"], meta)
        if not report["has_data"] and not bgt["has_rows"]:
            continue
        reports.append(report)
        bgt_by_cc[cc] = bgt
        if "2" in sheets:
            ho_by_cc[cc] = ho_report.build_ho_report(company_id, cc, f["yy"], f["mm"], f["coas"], f["cats"])
        if "3" in sheets:
            append_by_cc[cc] = service.query_append(company_id, cc, f["yy"], f["mm"], f["coas"], cats=f["cats"])["rows"]
    if not reports:
        return jsonify({"ok": False, "pesan": "Tidak ada data untuk diexport."}), 404
    data = exports.build_zip(reports, f, ho_by_cc, append_by_cc, bgt_by_cc)
    suffix = {"1": " sheet 1", "12": " sheet 1-2", "123": ""}[sheets]
    return _attachment(data, f"Management Report {date.today().isoformat()}{suffix}.zip", "application/zip")
