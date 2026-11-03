# tests/test_prportal_siswa.py -- profil siswa lengkap (disamarkan) + ubah data siswa dari PR Portal (fn_prp_update_siswa)
import os, sys, json, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import config
from database import get_conn
from tests.test_prportal_fn import _siswa, _budget

COMPANY_ID = 2


def _fn(sql, *args):
    conn = get_conn()
    try:
        return json.loads(conn.execute(sql, args).fetchone()[0])
    finally:
        conn.close()


def _budget_siswa(code):
    return _fn("SELECT fn_prp_budget_siswa(?)::text", code)


def _update(code, fields, by="harry@sinarmas.test"):
    return _fn("SELECT fn_prp_update_siswa(?::jsonb)::text", json.dumps({"code": code, "requested_by": by, "fields": fields}))


def _row(code):
    conn = get_conn()
    try:
        return dict(conn.execute("SELECT * FROM siswa WHERE code=?", (code,)).fetchone())
    finally:
        conn.close()


def _setup():
    _siswa("D1", "Ryan Eka Cahya", norek="1234-5678-6703", bank="Bank Sinarmas KCP Suprapto", namarek="Ryan Eka Cahya")
    conn = get_conn()
    conn.execute("UPDATE siswa SET tanggal_lahir='2000-05-17', prodi='Hukum', fakultas='FH', universitas='UNISSULA', referensi='ref-1',"
                 " catatan='cat umum', catatan_budget='RAHASIA BUDGET', catatan_payment='RAHASIA PAYMENT', group_setf='1.1',"
                 " angkatan=2022, angkatan_kuliah='2022', ipk_sem1=3.5 WHERE code='D1'")
    conn.commit(); conn.close()
    _budget("D1")


def test_detail_has_profile_and_masks_rekening_fields():
    _setup()
    s = _budget_siswa("D1")["siswa"]
    assert s["nama"] == "Ryan Eka Cahya" and s["tanggal_lahir"] == "2000-05-17" and s["prodi"] == "Hukum"
    assert s["angkatan"] == 2022 and s["group_setf"] == "1.1" and s["universitas"] == "UNISSULA" and s["ipk_sem1"] == 3.5
    assert s["bank_masked"] == "B*** S*** K*** S***" and s["nama_rekening_masked"] == "R*** E*** C***"
    assert s["rekening_last4"] == "6703" and s["rekening_ok"] is True
    blob = json.dumps(s)
    for secret in ("Sinarmas", "Suprapto", "1234-5678-6703", "123456786703", "RAHASIA", "norek", "namarek"):
        assert secret not in blob, secret
    assert "bank" not in s and "nama_rekening" not in s and "catatan_budget" not in s and "catatan_payment" not in s


def test_update_changes_only_sent_fields_and_returns_masked_detail():
    _setup()
    before = _row("D1")
    res = _update("D1", {"nama": "  Ryan Eka Cahya S.H. ", "prodi": "Ilmu Hukum", "ipk_sem2": 3.75, "angkatan": 2023,
                         "status": "lulus", "tanggal_lahir": "2000-05-18"})
    assert res["ok"] is True and res["changed"] == 6, res
    assert res["siswa"]["nama"] == "Ryan Eka Cahya S.H." and res["siswa"]["status"] == "lulus"
    assert "Sinarmas" not in json.dumps(res)
    after = _row("D1")
    assert after["prodi"] == "Ilmu Hukum" and after["ipk_sem2"] == 3.75 and after["angkatan"] == 2023
    assert after["updated_by"] == "prportal:harry@sinarmas.test" and after["updated_at"]
    # field lain, termasuk yang tidak boleh diubah, utuh
    for k in ("code", "bank", "norek", "namarek", "group_setf", "fakultas", "universitas", "referensi", "catatan",
              "catatan_budget", "catatan_payment", "ipk_sem1", "angkatan_kuliah"):
        assert after[k] == before[k], k


@pytest.mark.parametrize("field", ["code", "bank", "norek", "namarek", "group_setf", "catatan_budget", "catatan_payment", "id", "company_id", "xyz"])
def test_update_rejects_readonly_or_unknown_fields_without_writes(field):
    _setup()
    before = _row("D1")
    res = _update("D1", {"prodi": "Baru", field: "x"})
    assert res["ok"] is False and "tidak boleh diubah" in res["pesan"]
    assert _row("D1") == before


@pytest.mark.parametrize("fields", [
    {"nama": ""}, {"nama": "x" * 151}, {"nama": 5}, {"jenjang": "S9"}, {"program": "Ngawur"}, {"status": "AKTIF"},
    {"angkatan": 1999}, {"angkatan": "2022"}, {"angkatan": 2022.5}, {"tanggal_lahir": "17-05-2000"}, {"tanggal_lahir": "2000-02-30"},
    {"ipk_sem1": 4.01}, {"ipk_sem1": -0.1}, {"ipk_sem1": "3"}, {"ipk_pen3": 5}, {"ipk_sem11": 3}, {"prodi": "p" * 201},
    {"catatan": "c" * 1001}, {"prodi": None}, {},
])
def test_update_rejects_invalid_values_without_writes(fields):
    _setup()
    before = _row("D1")
    res = _update("D1", dict({"fakultas": "Fakultas Baru"}, **fields) if fields else fields)
    assert res["ok"] is False
    assert _row("D1") == before


def test_update_unknown_siswa_and_bad_payload():
    _setup()
    assert _update("NOPE", {"prodi": "x"})["pesan"] == "Siswa tidak ditemukan."
    assert _fn("SELECT fn_prp_update_siswa(?::jsonb)::text", json.dumps({"code": "D1", "fields": {"prodi": "x"}}))["ok"] is False
    assert _fn("SELECT fn_prp_update_siswa(?::jsonb)::text", json.dumps({"code": "D1", "requested_by": "a@b", "fields": []}))["ok"] is False


def test_sql_value_lists_match_flow_config():
    sql = open(os.path.join(os.path.dirname(__file__), "..", "db_migrations", "0006_fn_prportal.sql"), encoding="utf-8").read()
    body = sql[sql.index("fn_prp_siswa_field_error"):]
    def lst(after):
        seg = body[body.index(after):]
        seg = seg[seg.index("array["):seg.index("])")]
        return re.findall(r"''([^']+)''", seg)
    assert lst("p_key = ''jenjang''") == config.JENJANG
    assert lst("p_key = ''program''") == config.PROGRAM
    assert lst("p_key = ''status''") == config.STATUS_SISWA
