# modules/general_ledger/routes.py
import io

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import get_jwt

from auth.middleware import is_admin, json_admin_required, jwt_html_required
from modules.general_ledger import service
from modules.general_ledger import sync as gl_sync
from modules.general_ledger.parser import COLUMNS, LABELS, ParseError, read_gl_sheet

bp = Blueprint("general_ledger", __name__, url_prefix="/general-ledger")



def _gl_num(value) -> str:
    """1234567.0 -> '1.234.567' (Indonesian thousands separator); None -> ''."""
    if value is None:
        return ""
    return f"{float(value):,.0f}".replace(",", ".")


bp.add_app_template_filter(_gl_num, "gl_num")

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
        entity=entity, ent=ent, entities=service.ENTITIES, filters=filters, result=result,
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
