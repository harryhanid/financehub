# modules/payment_memo/api.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import config
from auth.middleware import api_role_required
from modules.payment_memo.service import (
    get_draft_payments,
    get_memo_list,
    create_memo,
)
from database import get_conn

memo_api = Blueprint("memo_api", __name__, url_prefix="/api/v1")

_COMPANY_ID = {c["code"]: c["id"] for c in config.COMPANIES}


def _cid(code):
    return _COMPANY_ID.get(code)


def _ccode(cid):
    for c in config.COMPANIES:
        if c["id"] == cid:
            return c["code"]
    return ""


def ok(data, status=200):
    return jsonify({"ok": True, "data": data}), status


def err(msg, status=400):
    return jsonify({"ok": False, "pesan": msg}), status


@memo_api.get("/payment-draft")
@jwt_required(locations=["headers"])
def api_draft_payments():
    code = request.args.get("company", "")
    cid = _cid(code)
    if not cid:
        return err("company harus SMT atau ETF")
    rows = get_draft_payments(cid)
    return ok(rows)


@memo_api.get("/payment-memo")
@jwt_required(locations=["headers"])
def api_list_memo():
    code = request.args.get("company", "")
    cid = _cid(code)
    if not cid:
        return err("company harus SMT atau ETF")
    status = request.args.get("status", "")
    rows = get_memo_list(cid, status=status)
    return ok(rows)


@memo_api.post("/payment-memo")
@jwt_required(locations=["headers"])
@api_role_required("verificator")
def api_create_memo():
    body = request.get_json(force=True) or {}
    code = body.get("company", "")
    cid = _cid(code)
    if not cid:
        return err("company harus SMT atau ETF")

    tanggal = body.get("tanggal", "")
    if not tanggal:
        return err("tanggal wajib diisi")
    try:
        from datetime import datetime as _dt
        _dt.strptime(tanggal, "%Y-%m-%d")
    except ValueError:
        return err("Format tanggal tidak valid (YYYY-MM-DD)")

    notes = body.get("notes", "")
    raw_ids = body.get("item_ids", [])
    try:
        item_ids = [int(i) for i in raw_ids]
    except (TypeError, ValueError):
        return err("item_ids harus berisi integer")

    claims = get_jwt()
    created_by = claims.get("username", "")

    # Look up draft payments by ID to build items list
    items = []
    if item_ids:
        conn = get_conn()
        placeholders = ",".join("?" * len(item_ids))
        rows = conn.execute(
            f"""SELECT pb.id, pb.amount, pb.siswa_code, s.nama, s.bank, s.norek, s.namarek
                FROM payment_beasiswa pb
                LEFT JOIN siswa s ON s.company_id=pb.company_id AND s.code=pb.siswa_code
                WHERE pb.id IN ({placeholders}) AND pb.company_id=? AND pb.status='draft'""",
            (*item_ids, cid)
        ).fetchall()
        conn.close()
        for r in rows:
            items.append({
                "source_module": "beasiswa",
                "source_id": r["id"],
                "description": r["nama"] or r["siswa_code"],
                "amount": r["amount"],
                "vendor": r["nama"] or "",
                "bank_account": f"{r['bank']} {r['norek']}".strip() if r["norek"] else "",
            })

    result = create_memo(cid, code, tanggal, notes, created_by, items)
    if result.get("ok"):
        return jsonify(result), 201
    return jsonify(result), 400
