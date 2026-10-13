# modules/general_ledger/routes.py
import io

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import get_jwt

from auth.middleware import is_admin, json_admin_required, jwt_html_required
from modules.general_ledger import coa_map, mr_report, mr_rows, service
from modules.general_ledger import sync as gl_sync
from modules.general_ledger.parser import COLUMNS, LABELS, ParseError, read_gl_sheet

bp = Blueprint("general_ledger", __name__, url_prefix="/general-ledger")



def _gl_num(value) -> str:
    """1234567.0 -> '1.234.567' (Indonesian thousands separator); None -> ''."""
    if value is None:
        return ""
    return f"{float(value):,.0f}".replace(",", ".")


bp.add_app_template_filter(_gl_num, "gl_num")


def _gl_mio(value) -> str:
    """Rp Mio with 1 decimal, Indonesian style: 1234.56 -> '1.234,6'; None -> ''."""
    if value is None:
        return ""
    v = round(float(value), 1) + 0.0                 # never "-0,0"
    return f"{v:,.1f}".replace(",", "\0").replace(".", ",").replace("\0", ".")


bp.add_app_template_filter(_gl_mio, "gl_mio")

_FILTER_KEYS = ("date_from", "date_to", "acc", "job", "q")
_NUMERIC = {"debit", "credit", "qty_awal", "qty_akhir", "harga_satuan", "debit_credit"}


def _entity_or_404(entity):
    if entity not in service.ENTITIES:
        abort(404)
    return service.ENTITIES[entity]


def _page():
    try:
        return int(request.args.get("page", 1))
    except (TypeError, ValueError):
        return 1


@bp.route("/", methods=["GET"])
@jwt_html_required
def index():
    return redirect(url_for("general_ledger.entity_page", entity="smt"))


@bp.route("/<entity>", methods=["GET"])
@jwt_html_required
def entity_page(entity):
    ent = _entity_or_404(entity)
    filters = {k: (request.args.get(k) or "").strip() for k in _FILTER_KEYS}
    result = service.query_rows(entity, {k: v for k, v in filters.items() if v}, page=_page())
    try:
        can_manage = is_admin(get_jwt())
    except Exception:
        can_manage = False
    return render_template(
        "general_ledger/index.html",
        entity=entity, active_tab=entity, ent=ent, entities=service.ENTITIES, filters=filters, result=result,
        columns=[(c, LABELS[c]) for c in COLUMNS], numeric=_NUMERIC,
        last=service.last_sync(entity), syncs=service.list_syncs(entity, 5),
        can_manage=can_manage, active_page="general_ledger", use_unified_header=True,
    )


@bp.route("/<entity>/sync", methods=["POST"])
@json_admin_required
def sync_excel(entity):
    if entity not in service.ENTITIES:
        return jsonify({"ok": False, "pesan": "Entitas tidak dikenal."}), 404
    ent = service.ENTITIES[entity]
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "pesan": "File belum dipilih."}), 400
    if not f.filename.lower().endswith(".xlsb"):
        return jsonify({"ok": False, "pesan": "File harus berformat .xlsb."}), 400
    try:
        result = read_gl_sheet(io.BytesIO(f.read()), ent["sheet"])
        if not result.rows:
            raise ParseError(f"Tidak ada baris data yang valid di sheet {ent['sheet']}.")
    except ParseError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    try:
        out = gl_sync.sync_rows(entity, f.filename, get_jwt().get("username", ""),
                                result.rows, result.dropped)
    except Exception as e:
        return jsonify({"ok": False, "pesan": f"Sync gagal, data lama tidak berubah: {e}"}), 500
    if not out["changed"]:
        pesan = f"Sudah sinkron: tidak ada perubahan sejak sync terakhir ({out['rows']} baris)."
    else:
        s = out["summary"]
        pesan = (f"Sync {ent['label']} selesai: {out['rows']} baris "
                 f"({s['added']} baru, {s['removed']} dihapus, {s['changed']} berubah; "
                 f"{result.dropped} baris dilewati).")
    if not out["balanced"]:
        pesan += " Peringatan: total Debit dan Credit tidak balance."
    return jsonify({"ok": True, "dropped": result.dropped, "pesan": pesan, **out})


def _int_arg(name):
    try:
        return int(request.args.get(name))
    except (TypeError, ValueError):
        return None


def _resolve_period(opts):
    """Requested year/month if valid, otherwise the latest period that has data."""
    yy = _int_arg("yy")
    if yy not in opts["yys"]:
        yy = opts["yys"][-1] if opts["yys"] else None
    if yy is None:
        return None, None
    months = opts["months"][yy]
    mm = _int_arg("mm")
    return yy, (mm if mm in months else months[-1])


@bp.route("/mr", methods=["GET"])
@jwt_html_required
def mr_page():
    cmap = coa_map.get_map()
    built = mr_rows.build_mr_rows(
        {"SMT": service.load_mr_source("smt"), "ETF": service.load_mr_source("etf")}, cmap)
    opts = mr_rows.period_options(built.rows)
    yy, mm = _resolve_period(opts)
    scoped = mr_rows.apply_cutoff(built.rows, yy, mm) if yy is not None else []
    cc = (request.args.get("cc") or "").strip()
    ccs = mr_report.list_ccs(scoped)
    if cc not in ccs:
        cc = ""                                       # stale/unknown CC: same as "All Cost Center"
    view = "data" if request.args.get("view") == "data" else "report"
    q = (request.args.get("q") or "").strip()
    report = mr_report.build_report(scoped, cc or None) if view == "report" else None
    data = mr_report.query_data(scoped, q=q, cc=cc or None, page=_page()) if view == "data" else None
    shown = [r for r in scoped if not cc or r["cc"] == cc]
    unmapped = mr_rows.unmapped_summary(scoped)
    n_rows, total_act = len(shown), round(sum(r["act"] for r in shown), 6) + 0.0
    if data is not None:
        n_rows, total_act = data["total"], data["sum_act"]
    try:
        can_manage = is_admin(get_jwt())
    except Exception:
        can_manage = False
    return render_template(
        "general_ledger/mr.html",
        entities=service.ENTITIES, active_tab="mr", can_manage=can_manage,
        last_coa=coa_map.last_sync(), has_map=bool(cmap), has_gl=bool(built.rows),
        opts=opts, yy=yy, mm=mm, cc=cc, q=q, view=view, ccs=ccs,
        report=report, data=data, n_rows=n_rows, total_act=total_act,
        unmapped=unmapped, unmapped_rows=sum(u["rows"] for u in unmapped),
        unmapped_act=round(sum(u["act"] for u in unmapped), 6) + 0.0,
        skipped_date=built.skipped_date, active_page="general_ledger", use_unified_header=True,
    )


@bp.route("/mr/sync-coa", methods=["POST"])
@json_admin_required
def sync_coa():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "pesan": "File belum dipilih."}), 400
    if not f.filename.lower().endswith(".xlsb"):
        return jsonify({"ok": False, "pesan": "File harus berformat .xlsb."}), 400
    try:
        rows, cc_rows = coa_map.read_mapping_sheets(io.BytesIO(f.read()))
        if not rows:
            raise coa_map.CoaParseError("Tidak ada pemetaan COA yang valid di sheet COA.")
    except coa_map.CoaParseError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    try:
        out = coa_map.sync_coa(f.filename, get_jwt().get("username", ""), rows, cc_rows)
    except Exception as e:
        return jsonify({"ok": False, "pesan": f"Sync gagal, pemetaan lama tidak berubah: {e}"}), 500
    if not out["changed"]:
        pesan = (f"Sudah sinkron: pemetaan tidak berubah (SMT {out['rows_smt']} akun, "
                 f"ETF {out['rows_etf']} akun, {out['rows_cc']} cost center).")
    else:
        pesan = (f"Sync pemetaan selesai: SMT {out['rows_smt']} akun, "
                 f"ETF {out['rows_etf']} akun, {out['rows_cc']} cost center.")
    return jsonify({"ok": True, "pesan": pesan, **out})
