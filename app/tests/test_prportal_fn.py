# tests/test_prportal_fn.py -- fungsi baca PR Portal (migrasi 0006): cari siswa & budget siswa.
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_conn

COMPANY_ID = 2  # ETF


def _siswa(code, nama, status="Aktif", norek="123-456-7890", bank="BCA", namarek="Nama Rek", **kw):
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama, jenjang, program, universitas, bank, norek, namarek, status,"
        " ipk_sem1, ipk_sem2) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (COMPANY_ID, code, nama, "S1", "SMART", "UI", bank, norek, namarek, status,
         kw.get("ipk1", 3.1), kw.get("ipk2", 3.4)))
    conn.commit()
    conn.close()


def _budget(code, cat1="By Pendidikan", cat2="Semester 1", amount=1000, status="open",
            tanggal="2026-01-01", tgl_expired=None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO budget_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, status, tgl_expired)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (COMPANY_ID, code, cat1, cat2, tanggal, amount, status, tgl_expired))
    conn.commit()
    conn.close()


def _call(fn, arg):
    # jsonb WAJIB di-cast ::text: fhdb mem-parse kolom jsonb dengan object_pairs_hook=list, sehingga
    # objek bersarang kembali sebagai list pasangan (key, value), bukan dict. Teks di-json.loads di _j.
    conn = get_conn()
    try:
        return conn.execute(f"SELECT {fn}(?)::text", (arg,)).fetchone()[0]
    finally:
        conn.close()


def _j(v):
    return None if v is None else json.loads(v)


def test_search_min_3_chars():
    _siswa("A1", "Abi")
    _budget("A1")
    assert _j(_call("fn_prp_search_siswa", "ab")) == []
    assert _j(_call("fn_prp_search_siswa", "  a ")) == []


def test_search_only_aktif_with_open_budget():
    _siswa("S1", "Zed Aktif"); _budget("S1")
    _siswa("S2", "Zed Lulus", status="lulus"); _budget("S2")
    _siswa("S3", "Zed Complete"); _budget("S3", status="complete")
    res = _j(_call("fn_prp_search_siswa", "zed"))
    assert [r["code"] for r in res] == ["S1"]


def test_search_max_10():
    for i in range(12):
        _siswa(f"M{i:02d}", f"Many {i:02d}")
        _budget(f"M{i:02d}")
    assert len(_j(_call("fn_prp_search_siswa", "many"))) == 10


def test_search_masks_rekening():
    _siswa("R1", "Rek Satu", norek="123-456-7890"); _budget("R1")
    _siswa("R2", "Rek Dua", norek="12"); _budget("R2")
    raw = _call("fn_prp_search_siswa", "rek")
    text = raw
    assert "1234567890" not in text and "123-456-7890" not in text
    by = {r["code"]: r for r in _j(raw)}
    assert by["R1"]["rekening_last4"] == "7890" and by["R1"]["rekening_ok"] is True
    assert by["R2"]["rekening_ok"] is False
    assert by["R1"]["ipk_terakhir"] == 3.4
    assert by["R1"]["nama_rekening"] == "Nama Rek"


def test_budget_siswa_status_and_order():
    _siswa("B1", "Bud Satu")
    _budget("B1", "By Tunjangan", "Semester 2")
    _budget("B1", "By Pendidikan", "Semester 10")
    _budget("B1", "By Pendidikan", "Semester 2")
    res = _j(_call("fn_prp_budget_siswa", "B1"))
    assert [(r["cat1"], r["cat2"]) for r in res["rows"]] == [
        ("By Pendidikan", "Semester 2"), ("By Pendidikan", "Semester 10"), ("By Tunjangan", "Semester 2")]
    assert all(r["status"] == "open" for r in res["rows"])
    assert res["siswa"]["code"] == "B1" and res["siswa"]["status"] == "Aktif"
    assert _j(_call("fn_prp_budget_siswa", "TIDAKADA")) is None


def test_budget_siswa_non_aktif():
    _siswa("N1", "Non Aktif", status="gugur")
    _budget("N1"); _budget("N1", cat2="Semester 2", status="complete")
    res = _j(_call("fn_prp_budget_siswa", "N1"))
    assert len(res["rows"]) == 2 and all(r["status"] == "non_aktif" for r in res["rows"])


def test_budget_siswa_hides_expired():
    _siswa("E1", "Exp Satu")
    _budget("E1", cat2="Semester 1", tgl_expired="2000-01-01")
    _budget("E1", cat2="Semester 2", tgl_expired="")
    _budget("E1", cat2="Semester 3", tgl_expired=None)
    res = _j(_call("fn_prp_budget_siswa", "E1"))
    assert [r["cat2"] for r in res["rows"]] == ["Semester 2", "Semester 3"]


def test_budget_siswa_on_progress_shows_pa_number():
    _siswa("P1", "Prog Satu")
    _budget("P1", status="on_progress")
    conn = get_conn()
    bid = conn.execute("SELECT id FROM budget_beasiswa WHERE siswa_code='P1'").fetchone()["id"]
    sid = conn.execute("SELECT id FROM siswa WHERE code='P1'").fetchone()["id"]
    conn.execute("INSERT INTO etf_pa (company_id, pa_number, created_at) VALUES (?,?,?)",
                 (COMPANY_ID, "PA/ETF/001/2026", "2026-10-27T00:00:00"))
    pa_id = conn.execute("SELECT id FROM etf_pa").fetchone()["id"]
    conn.execute("INSERT INTO etf_pa_lines (pa_id, student_id, budget_id) VALUES (?,?,?)", (pa_id, sid, bid))
    conn.commit()
    conn.close()
    res = _j(_call("fn_prp_budget_siswa", "P1"))
    assert res["rows"][0]["pa_number"] == "PA/ETF/001/2026"
    assert res["rows"][0]["status"] == "on_progress"
