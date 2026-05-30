# modules/beasiswa/api.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
import config
from modules.beasiswa.service import (
    get_siswa_list,
    get_rekap,
    get_payment,
    get_budget,
)

beasiswa_api = Blueprint("beasiswa_api", __name__, url_prefix="/api/v1")

_COMPANY_ID = {c["code"]: c["id"] for c in config.COMPANIES}


def _cid(code):
    return _COMPANY_ID.get(code)


def ok(data, status=200):
    return jsonify({"ok": True, "data": data}), status


def err(msg, status=400):
    return jsonify({"ok": False, "pesan": msg}), status


@beasiswa_api.get("/siswa")
@jwt_required(locations=["headers"])
def api_list_siswa():
    code = request.args.get("company", "")
    cid = _cid(code)
    if not cid:
        return err("company harus SMT atau ETF")
    search = request.args.get("search", "")
    status = request.args.get("status", "")
    program = request.args.get("program", "")
    rows = get_siswa_list(cid, search=search, status=status, program=program)
    return ok(rows)


@beasiswa_api.get("/rekap")
@jwt_required(locations=["headers"])
def api_rekap():
    code = request.args.get("company", "")
    cid = _cid(code)
    if not cid:
        return err("company harus SMT atau ETF")
    program = request.args.get("program", "")
    pillar = request.args.get("pillar", "")
    status = request.args.get("status", "")
    rows = get_rekap(cid, program=program, pillar=pillar, status=status)
    return ok(rows)


@beasiswa_api.get("/payment-beasiswa")
@jwt_required(locations=["headers"])
def api_list_payment():
    code = request.args.get("company", "")
    cid = _cid(code)
    if not cid:
        return err("company harus SMT atau ETF")
    siswa_code = request.args.get("siswa_code", "")
    status = request.args.get("status", "")
    rows = get_payment(cid, siswa_code=siswa_code, status=status)
    return ok(rows)


@beasiswa_api.get("/budget")
@jwt_required(locations=["headers"])
def api_budget():
    code = request.args.get("company", "")
    cid = _cid(code)
    if not cid:
        return err("company harus SMT atau ETF")
    siswa_code = request.args.get("siswa_code", "")
    if not siswa_code:
        return err("siswa_code wajib diisi")
    data = get_budget(cid, siswa_code)
    return ok(data)
