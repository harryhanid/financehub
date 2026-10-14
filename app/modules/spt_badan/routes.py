# modules/spt_badan/routes.py
import io
from urllib.parse import urlencode

import openpyxl
from flask import Blueprint, abort, jsonify, render_template, request, send_file, session
from flask_jwt_extended import get_jwt

from auth.middleware import is_admin, json_admin_required, jwt_html_required
from modules.spt_badan import service

bp = Blueprint("spt_badan", __name__, url_prefix="/spt-badan")

KIND_LABELS = {
    "akun_belum_dipetakan": "Akun belum dipetakan", "category_lk_tidak_dikenal": "Category LK belum diatur",
    "category_spt_kosong": "Category SPT kosong", "pph_kosong": "Jenis PPh kosong",
    "pph_bukan_jenis": "Bukan jenis PPh", "kategori_gl_beda": "Kategori GL ≠ Pemetaan",
}


def _spt_num(value) -> str:
    """1234567.4 -> '1.234.567' (Indonesian thousands separator); None -> ''."""
    if value is None:
        return ""
    return f"{float(value):,.0f}".replace(",", ".")


bp.add_app_template_filter(_spt_num, "spt_num")


@bp.app_context_processor
def _pager_helpers():
    def pager_url(page):
        args = request.args.to_dict(flat=False)
        args["page"] = [str(page)]
        return "?" + urlencode(args, doseq=True)
    return {"pager_url": pager_url}


def _ctx():
    try:
        claims = get_jwt()
        return {"current_user": claims.get("username", ""), "current_role": claims.get("role", ""),
                "can_manage": is_admin(claims), "company_id": session.get("company_id"),
                "company_code": session.get("company_code"), "company_name": session.get("company_name")}
    except Exception:
        return {}


def _page():
    try:
        return max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        return 1


def _period_or_404(pid):
    period = service.get_period(pid)
    if period is None:
        abort(404)
    return period


def _render(template, period, **extra):
    snapshot = service.get_current_snapshot(period["id"])
    stale = service.staleness(period, snapshot) if snapshot else []
    return render_template(
        template, period=period, snapshot=snapshot, stale=stale, entity_label=service.ENTITIES[period["entity"]]["label"],
        kind_labels=KIND_LABELS, active_page="spt_badan", use_unified_header=True, **_ctx(), **extra)


@bp.route("/")
@jwt_html_required
def index():
    periods = []
    for p in service.list_periods():
        snap = service.get_current_snapshot(p["id"])
        periods.append({**p, "snapshot": snap, "stale": bool(snap and service.staleness(p, snap)),
                        "entity_label": service.ENTITIES[p["entity"]]["label"]})
    return render_template("spt_badan/index.html", periods=periods, entities=service.ENTITIES,
                           active_page="spt_badan", use_unified_header=True, **_ctx())


@bp.route("/periods", methods=["POST"])
@json_admin_required
def create_period():
    d = request.get_json(silent=True) or {}
    try:
        pid = service.create_period(d.get("entity", ""), d.get("tax_year"), get_jwt().get("username", ""),
                                    label=d.get("label") or "Simulasi YTD")
    except ValueError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    return jsonify({"ok": True, "id": pid, "pesan": "Periode dibuat."})


@bp.route("/<int:pid>")
@jwt_html_required
def detail(pid):
    period = _period_or_404(pid)
    snapshot = service.get_current_snapshot(pid)
    ctrls = service.get_controls(period, snapshot) if snapshot else []
    summary = service.income_statement_for(snapshot["id"])["summary"] if snapshot else None
    blockers = sum(1 for c in ctrls if c["status"] == "gagal")
    return _render("spt_badan/detail.html", period, active_tab="detail", steps=service.step_statuses(snapshot, ctrls),
                   summary=summary, blockers=blockers, controls=ctrls)


@bp.route("/<int:pid>/snapshot", methods=["POST"])
@json_admin_required
def snapshot(pid):
    period = service.get_period(pid)
    if period is None:
        return jsonify({"ok": False, "pesan": "Periode tidak ditemukan."}), 404
    try:
        sid = service.take_snapshot(pid, get_jwt().get("username", ""))
    except ValueError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "pesan": f"Snapshot gagal, snapshot sebelumnya tidak berubah: {e}"}), 500
    snap = service.get_current_snapshot(pid)
    blockers = sum(1 for c in service.get_controls(period, snap) if c["status"] == "gagal")
    pesan = f"Snapshot selesai: {snap['row_count']} baris GL; {blockers} kontrol wajib gagal."
    return jsonify({"ok": True, "pesan": pesan, "snapshot_id": sid, "blockers": blockers})


@bp.route("/<int:pid>/laba-rugi")
@jwt_html_required
def income_statement(pid):
    period = _period_or_404(pid)
    snapshot = service.get_current_snapshot(pid)
    statement = service.income_statement_for(snapshot["id"]) if snapshot else None
    return _render("spt_badan/laba_rugi.html", period, active_tab="laba_rugi", statement=statement)


@bp.route("/<int:pid>/baris")
@jwt_html_required
def drill(pid):
    period = _period_or_404(pid)
    snapshot = service.get_current_snapshot(pid)
    cats = [c for c in request.args.getlist("cats") if c]
    spt = request.args.get("spt") if "spt" in request.args else None
    sign = -1 if request.args.get("sign") == "-1" else 1
    data = service.drill_lines(snapshot["id"], cats, spt, page=_page()) if snapshot else None
    return _render("spt_badan/baris.html", period, active_tab="laba_rugi", data=data, cats=cats, spt=spt,
                   sign=sign)


@bp.route("/<int:pid>/pengecualian")
@jwt_html_required
def exceptions(pid):
    period = _period_or_404(pid)
    snapshot = service.get_current_snapshot(pid)
    kind = request.args.get("kind") if request.args.get("kind") in KIND_LABELS else ""
    severity = request.args.get("severity") if request.args.get("severity") in ("blocker", "warning") else ""
    q = (request.args.get("q") or "").strip()
    data = groups = None
    if snapshot:
        groups = service.exception_groups(snapshot["id"])
        data = service.list_exceptions(snapshot["id"], kind, severity, q, page=_page())
    return _render("spt_badan/pengecualian.html", period, active_tab="pengecualian", groups=groups, data=data,
                   kind=kind, severity=severity, q=q)


def _safe_cell(value):
    """Prefix text that Excel would read as a formula so it is stored and shown as plain text."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", chr(9), chr(13)):
        return "'" + value
    return value


@bp.route("/<int:pid>/pengecualian.xlsx")
@jwt_html_required
def exceptions_xlsx(pid):
    period = _period_or_404(pid)
    snapshot = service.get_current_snapshot(pid)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pengecualian"
    marker = f"Simulasi YTD — bukan SPT final · {service.ENTITIES[period['entity']]['label']} {period['tax_year']}"
    if snapshot:
        marker += (f" · snapshot {snapshot['taken_at']} · data {snapshot['date_min']} s.d. "
                   f"{snapshot['date_max']}")
        stale = service.staleness(period, snapshot)
    else:
        stale = []
    ws.append([_safe_cell(marker)])
    if stale:
        ws.append([_safe_cell("; ".join(stale))])
    ws.append(["Jenis", "Tingkat", "Akun", "Tanggal", "ID#", "Job", "Memo", "Debit - Credit", "PPh (GL)", "Keterangan"])
    if snapshot:
        for r in service.list_exceptions(snapshot["id"], per_page=10 ** 9)["rows"]:
            ws.append([_safe_cell(v) for v in (
                KIND_LABELS.get(r["kind"], r["kind"]), r["severity"], r["account"], r["tgl"], r["id_no"],
                r["job_name"], r["memo"], r["debit_credit"], r["pph_type_raw"], r["detail"])])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f"pengecualian-spt-{period['entity']}-{period['tax_year']}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@bp.route("/<int:pid>/kontrol")
@jwt_html_required
def controls_page(pid):
    period = _period_or_404(pid)
    snapshot = service.get_current_snapshot(pid)
    ctrls = service.get_controls(period, snapshot) if snapshot else []
    return _render("spt_badan/kontrol.html", period, active_tab="kontrol", controls=ctrls)
