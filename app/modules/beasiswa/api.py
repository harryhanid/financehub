# modules/beasiswa/api.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
import config
from modules.beasiswa.service import (
    get_siswa_list, get_siswa_detail, add_siswa, update_siswa,
    generate_kode_siswa,
    get_rekap,
    get_payment, add_payment_batch,
    get_budget, add_budget_batch,
)
from auth.middleware import api_role_required

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


@beasiswa_api.get("/siswa/<code>")
@jwt_required(locations=["headers"])
def api_get_siswa(code):
    company = request.args.get("company", "")
    cid = _cid(company)
    if not cid:
        return err("company harus SMT atau ETF")
    siswa = get_siswa_detail(cid, code)
    if not siswa:
        return err("Siswa tidak ditemukan", 404)
    return ok(siswa)


@beasiswa_api.post("/siswa")
@jwt_required(locations=["headers"])
@api_role_required("requester", "verificator", "releaser")
def api_add_siswa():
    body = request.get_json(force=True) or {}
    company = body.get("company", "")
    cid = _cid(company)
    if not cid:
        return err("company harus SMT atau ETF")
    if not body.get("nama"):
        return err("nama wajib diisi")
    if not body.get("jenjang"):
        return err("jenjang wajib diisi")
    if not body.get("angkatan"):
        return err("angkatan wajib diisi")
    if not body.get("code"):
        body["code"] = generate_kode_siswa(body["jenjang"], int(body["angkatan"]), cid)
    result = add_siswa(cid, body)
    if not result["ok"]:
        return err(result["pesan"])
    return ok({"code": body["code"]}, 201)


@beasiswa_api.put("/siswa/<code>")
@jwt_required(locations=["headers"])
@api_role_required("requester", "verificator", "releaser")
def api_update_siswa(code):
    body = request.get_json(force=True) or {}
    company = body.get("company", "")
    cid = _cid(company)
    if not cid:
        return err("company harus SMT atau ETF")
    result = update_siswa(cid, code, body)
    if not result["ok"]:
        return err(result["pesan"], 404)
    return ok({"code": code})


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


@beasiswa_api.get("/payment")
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


@beasiswa_api.post("/payment")
@jwt_required(locations=["headers"])
@api_role_required("requester")
def api_add_payment():
    body = request.get_json(force=True) or {}
    company = body.get("company", "")
    cid = _cid(company)
    if not cid:
        return err("company harus SMT atau ETF")
    for field in ["siswa_code", "tanggal", "pillar", "perusahaan", "cat1", "cat2", "amount"]:
        if not body.get(field):
            return err(f"Field wajib: {field}")
    items = [{"cat1": body["cat1"], "cat2": body["cat2"], "amount": body["amount"],
              "cat3": body.get("cat3", ""), "cat4": body.get("cat4", "")}]
    result = add_payment_batch(cid, body["siswa_code"], body["tanggal"],
                               body["pillar"], body["perusahaan"], items)
    if not result["ok"]:
        return err(result["pesan"])
    return ok({"saved": result["saved"]}, 201)


@beasiswa_api.get("/budget")
@jwt_required(locations=["headers"])
def api_get_budget():
    code = request.args.get("company", "")
    cid = _cid(code)
    if not cid:
        return err("company harus SMT atau ETF")
    siswa_code = request.args.get("siswa_code", "")
    if not siswa_code:
        return err("siswa_code wajib diisi")
    data = get_budget(cid, siswa_code)
    return ok(data)


@beasiswa_api.post("/budget")
@jwt_required(locations=["headers"])
@api_role_required("requester", "verificator", "releaser")
def api_add_budget():
    body = request.get_json(force=True) or {}
    company = body.get("company", "")
    cid = _cid(company)
    if not cid:
        return err("company harus SMT atau ETF")
    for field in ["siswa_code", "tanggal", "pillar", "cat1", "cat2", "amount"]:
        if not body.get(field):
            return err(f"Field wajib: {field}")
    items = [{"cat1": body["cat1"], "cat2": body["cat2"], "amount": body["amount"]}]
    result = add_budget_batch(cid, body["siswa_code"], body["tanggal"], body["pillar"], items)
    if not result["ok"]:
        return err(result["pesan"])
    return ok({"saved": result["saved"]}, 201)
