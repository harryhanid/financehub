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



def test_budget_siswa_cat2_long_digits_no_overflow():
    _siswa("L1", "Long Satu")
    _budget("L1", cat2="Semester 123456789012")
    _budget("L1", cat2="Semester 2")
    res = _j(_call("fn_prp_budget_siswa", "L1"))
    assert [r["cat2"] for r in res["rows"]] == ["Semester 2", "Semester 123456789012"]


def test_budget_pa_number_newest_pa_first():
    _siswa("P2", "Prog Dua")
    _budget("P2", status="on_progress")
    conn = get_conn()
    bid = conn.execute("SELECT id FROM budget_beasiswa WHERE siswa_code='P2'").fetchone()["id"]
    sid = conn.execute("SELECT id FROM siswa WHERE code='P2'").fetchone()["id"]
    for num in ("PA/ETF/001/2026", "PA/ETF/002/2026"):
        conn.execute("INSERT INTO etf_pa (company_id, pa_number, created_at) VALUES (?,?,?)",
                     (COMPANY_ID, num, "2026-10-27T00:00:00"))
        pa_id = conn.execute("SELECT id FROM etf_pa WHERE pa_number=?", (num,)).fetchone()["id"]
        conn.execute("INSERT INTO etf_pa_lines (pa_id, student_id, budget_id) VALUES (?,?,?)", (pa_id, sid, bid))
    conn.commit()
    conn.close()
    assert _j(_call("fn_prp_budget_siswa", "P2"))["rows"][0]["pa_number"] == "PA/ETF/002/2026"

# ---------------------------------------------------------------- fn_prp_submit_pa (Task 3)
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

_JENIS_CFG = {
    "agri": ("etf_pa", "etf_pa_lines", "ETF"),
    "app": ("app_pa", "app_pa_lines", "APP"),
    "sml": ("sml_pa", "sml_pa_lines", "SML"),
    "setf": ("setf_pa", "setf_pa_lines", "SETF"),
    "energy": ("energy_pa", "energy_pa_lines", "ENERGY"),
}


def _yyyy():
    return (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y")


def _budget_id(code, cat2, cat1="By Pendidikan"):
    conn = get_conn()
    try:
        return conn.execute("SELECT id FROM budget_beasiswa WHERE siswa_code=? AND cat1=? AND cat2=?",
                            (code, cat1, cat2)).fetchone()["id"]
    finally:
        conn.close()


def _payload(code, lines, jenis="agri", **kw):
    p = {
        "jenis": jenis, "siswa_code": code,
        "tgl_payment_application": "2026-10-27", "tgl_surat_pengajuan": "2026-10-20",
        "doc_received_by_educ": "", "received_pa_from_educ": None,
        "keterangan": "Pembayaran semester", "route": "gl", "klasifikasi": "Normal",
        "attachment_file_id": "file-123", "requested_by": "harry@sinarmas.test", "cost_center": "CC-01",
        "lines": lines,
    }
    p.update(kw)
    return p


def _submit(p):
    conn = get_conn()
    try:
        return json.loads(conn.execute("SELECT fn_prp_submit_pa(?::jsonb)::text",
                                       (json.dumps(p),)).fetchone()[0])
    finally:
        conn.close()


def _state():
    """Jumlah baris header/line kelima jenis + status semua budget -- harus sama sebelum & sesudah gagal."""
    conn = get_conn()
    try:
        counts = {}
        for pa_tbl, lines_tbl, _ in _JENIS_CFG.values():
            counts[pa_tbl] = conn.execute(f"SELECT count(*) AS n FROM {pa_tbl}").fetchone()["n"]
            counts[lines_tbl] = conn.execute(f"SELECT count(*) AS n FROM {lines_tbl}").fetchone()["n"]
        st = [tuple(r) for r in conn.execute("SELECT id, status FROM budget_beasiswa ORDER BY id").fetchall()]
        return counts, st
    finally:
        conn.close()


def _std_siswa(code="T1", **kw):
    _siswa(code, "Test " + code, **kw)
    _budget(code, "By Pendidikan", "Semester 1", amount=18662875)
    _budget(code, "By Tunjangan", "Semester 1", amount=12000000)


def _std_lines(code="T1"):
    conn = get_conn()
    try:
        rows = conn.execute("SELECT id, cat1 FROM budget_beasiswa WHERE siswa_code=? ORDER BY id",
                            (code,)).fetchall()
    finally:
        conn.close()
    amt = {"By Pendidikan": 18662875, "By Tunjangan": 10500000}
    return [{"budget_id": r["id"], "tahun_ajaran": "2026/2027", "jumlah": amt[r["cat1"]]} for r in rows]


def _assert_rejected(p, pesan):
    before = _state()
    res = _submit(p)
    assert res["ok"] is False
    assert res["pesan"] == pesan
    assert _state() == before


def test_submit_creates_pa_lines_and_locks_budget():
    _std_siswa("T1")
    lines = _std_lines("T1")
    res = _submit(_payload("T1", lines))
    assert res["ok"] is True
    assert res["pa_number"] == f"PA/ETF/001/{_yyyy()}"
    assert res["jenis"] == "agri"
    assert res["total"] == 29162875
    conn = get_conn()
    try:
        hdr = conn.execute("SELECT * FROM etf_pa WHERE id=?", (res["pa_id"],)).fetchone()
        assert hdr["status"] == "open" and hdr["source"] == "prportal"
        assert hdr["requested_by"] == "harry@sinarmas.test" and hdr["cost_center"] == "CC-01"
        assert hdr["company_id"] == COMPANY_ID and hdr["pa_number"] == res["pa_number"]
        assert hdr["route"] == "gl" and hdr["klasifikasi"] == "Normal"
        assert hdr["attachment_file_id"] == "file-123"
        assert hdr["tgl_payment_application"] == "2026-10-27"
        assert hdr["tgl_surat_pengajuan"] == "2026-10-20"
        assert hdr["doc_received_by_educ"] == "" and hdr["received_pa_from_educ"] == ""
        assert len(hdr["created_at"]) == 19 and hdr["created_at"][10] == "T"
        sid = conn.execute("SELECT id FROM siswa WHERE code='T1'").fetchone()["id"]
        rows = conn.execute("SELECT * FROM etf_pa_lines WHERE pa_id=? ORDER BY budget_id",
                            (res["pa_id"],)).fetchall()
        assert [(r["budget_id"], r["jenis_pembayaran"], r["semester"], r["jumlah_pembayaran"]) for r in rows] == [
            (lines[0]["budget_id"], "By Pendidikan", "Semester 1", 18662875),
            (lines[1]["budget_id"], "By Tunjangan", "Semester 1", 10500000)]
        assert all(r["student_id"] == sid and r["route"] == "gl" and r["tahun_ajaran"] == "2026/2027"
                   and r["ipk_sem_sebelumnya"] == 3.4 for r in rows)
        st = conn.execute("SELECT status FROM budget_beasiswa WHERE siswa_code='T1'").fetchall()
        assert [r["status"] for r in st] == ["on_progress", "on_progress"]
    finally:
        conn.close()
    view = _j(_call("fn_prp_budget_siswa", "T1"))
    assert all(r["status"] == "on_progress" and r["pa_number"] == res["pa_number"] for r in view["rows"])


@pytest.mark.parametrize("jenis", list(_JENIS_CFG))
def test_submit_each_jenis_goes_to_its_table(jenis):
    pa_tbl, lines_tbl, prefix = _JENIS_CFG[jenis]
    _std_siswa("J1")
    res = _submit(_payload("J1", _std_lines("J1"), jenis=jenis))
    assert res["ok"] is True and res["jenis"] == jenis
    assert res["pa_number"] == f"PA/{prefix}/001/{_yyyy()}"
    conn = get_conn()
    try:
        hdr = conn.execute(f"SELECT * FROM {pa_tbl} WHERE id=?", (res["pa_id"],)).fetchone()
        assert hdr["pa_number"] == res["pa_number"] and hdr["source"] == "prportal" and hdr["status"] == "open"
        assert conn.execute(f"SELECT count(*) AS n FROM {lines_tbl} WHERE pa_id=? AND budget_id IS NOT NULL",
                            (res["pa_id"],)).fetchone()["n"] == 2
        for other_pa, other_lines, _ in _JENIS_CFG.values():
            if other_pa != pa_tbl:
                assert conn.execute(f"SELECT count(*) AS n FROM {other_pa}").fetchone()["n"] == 0
                assert conn.execute(f"SELECT count(*) AS n FROM {other_lines}").fetchone()["n"] == 0
    finally:
        conn.close()


def test_submit_rejects_over_budget_without_writes():
    _std_siswa("O1")
    lines = _std_lines("O1")
    lines[1]["jumlah"] = 12000001
    _assert_rejected(_payload("O1", lines), "Jumlah By Tunjangan Semester 1 melebihi budget 12000000.")


def test_submit_rejects_on_progress_budget_names_pa():
    _std_siswa("G1")
    first = _submit(_payload("G1", _std_lines("G1")[:1]))
    assert first["ok"] is True
    _assert_rejected(_payload("G1", _std_lines("G1")),
                     f"Baris budget By Pendidikan Semester 1 sudah dipakai {first['pa_number']}.")


def test_submit_rejects_complete_budget():
    _siswa("C1", "Test C1")
    _budget("C1", amount=500, status="complete")
    line = {"budget_id": _budget_id("C1", "Semester 1"), "tahun_ajaran": "", "jumlah": 100}
    _assert_rejected(_payload("C1", [line]), "Baris budget By Pendidikan Semester 1 sudah Complete.")


def test_submit_rejects_budget_of_other_siswa():
    _std_siswa("X1")
    _std_siswa("X2")
    lines = _std_lines("X1")[:1] + _std_lines("X2")[:1]
    _assert_rejected(_payload("X1", lines), "Baris budget tidak ditemukan untuk siswa ini.")
    _assert_rejected(_payload("X1", [{"budget_id": 999999, "tahun_ajaran": "", "jumlah": 1}]),
                     "Baris budget tidak ditemukan untuk siswa ini.")


def test_submit_rejects_expired_budget():
    _siswa("Y1", "Test Y1")
    _budget("Y1", amount=500, tgl_expired="2000-01-01")
    line = {"budget_id": _budget_id("Y1", "Semester 1"), "tahun_ajaran": "", "jumlah": 100}
    _assert_rejected(_payload("Y1", [line]), "Baris budget tidak ditemukan untuk siswa ini.")


def test_submit_rejects_duplicate_budget_id():
    _std_siswa("D1")
    lines = _std_lines("D1")[:1]
    _assert_rejected(_payload("D1", lines + [dict(lines[0], jumlah=1)]), "Data PA tidak valid: budget_id.")


def test_submit_rejects_non_aktif_siswa():
    _std_siswa("NA", status="gugur")
    _assert_rejected(_payload("NA", _std_lines("NA")), "Siswa tidak aktif.")


def test_submit_rejects_incomplete_rekening():
    _std_siswa("RK", norek="12")
    _assert_rejected(_payload("RK", _std_lines("RK")), "Rekening siswa belum lengkap di Flow. Hubungi Finance.")


@pytest.mark.parametrize("jumlah", [0, -5, "100", 100.5])
def test_submit_rejects_bad_jumlah(jumlah):
    _std_siswa("BJ")
    lines = _std_lines("BJ")
    lines[0]["jumlah"] = jumlah
    _assert_rejected(_payload("BJ", lines), "Data PA tidak valid: jumlah.")


def test_submit_rejects_unknown_jenis():
    _std_siswa("UJ")
    _assert_rejected(_payload("UJ", _std_lines("UJ"), jenis="xyz"), "Jenis PA tidak dikenal.")


@pytest.mark.parametrize("field,value", [
    ("route", "cash"), ("klasifikasi", "Urgent"), ("tgl_payment_application", ""),
    ("tgl_payment_application", "27-10-2026"), ("tgl_payment_application", "2026-02-30"),
    ("tgl_surat_pengajuan", "kemarin"), ("requested_by", "  "), ("lines", []),
    ("siswa_code", "TIDAKADA"),
])
def test_submit_rejects_bad_shape(field, value):
    _std_siswa("BS")
    p = _payload("BS", _std_lines("BS"))
    p[field] = value
    _assert_rejected(p, f"Data PA tidak valid: {field}.")


def test_submit_rejects_too_many_lines():
    _std_siswa("TM")
    line = _std_lines("TM")[0]
    lines = [dict(line, budget_id=line["budget_id"] + i) for i in range(51)]
    _assert_rejected(_payload("TM", lines), "Data PA tidak valid: lines.")


def test_submit_concurrent_same_budget_one_wins(pg_dsn):
    import psycopg2
    import config

    _std_siswa("CC")
    p = json.dumps(_payload("CC", _std_lines("CC")))
    sql = "select fn_prp_submit_pa(%s::jsonb)::text"

    def connect():
        c = psycopg2.connect(pg_dsn)
        with c.cursor() as cur:
            cur.execute("set search_path to " + config.DB_SCHEMA)
        c.commit()
        return c

    a, b, watch = connect(), connect(), connect()
    watch.autocommit = True
    out = {}
    try:
        with b.cursor() as cur:
            cur.execute("select pg_backend_pid()")
            b_pid = cur.fetchone()[0]
        b.commit()
        with a.cursor() as cur:
            cur.execute(sql, (p,))
            res_a = json.loads(cur.fetchone()[0])  # transaksi A belum di-commit
        assert res_a["ok"] is True

        def run_b():
            try:
                with b.cursor() as cur:
                    cur.execute(sql, (p,))
                    out["res"] = json.loads(cur.fetchone()[0])
                b.commit()
            except Exception as e:  # dilaporkan lewat assert di bawah
                out["err"] = e

        t = threading.Thread(target=run_b, daemon=True)
        t.start()
        deadline = time.monotonic() + 10
        blocked = False
        while time.monotonic() < deadline and t.is_alive():
            with watch.cursor() as cur:
                cur.execute("select wait_event_type from pg_stat_activity where pid=%s", (b_pid,))
                row = cur.fetchone()
            if row and row[0] == "Lock":
                blocked = True
                break
            time.sleep(0.02)
        assert blocked, "B seharusnya menunggu lock milik A"
        a.commit()
        t.join(timeout=10)
        assert not t.is_alive()
        assert "err" not in out, out.get("err")
        assert res_a["pa_number"].startswith("PA/ETF/001/")
        assert out["res"]["ok"] is False
        assert out["res"]["pesan"] == (
            f"Baris budget By Pendidikan Semester 1 sudah dipakai {res_a['pa_number']}.")
    finally:
        for c in (a, b, watch):
            try:
                c.rollback()
            except Exception:
                pass
            c.close()
    counts, _ = _state()
    assert counts["etf_pa"] == 1 and counts["etf_pa_lines"] == 2
