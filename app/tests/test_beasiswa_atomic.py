"""Task 15b (atomic-flows.md): alur multi-tulisan beasiswa harus all-or-nothing di Postgres, plus
penomoran PAM (fn_next_pam_no, R24), R25 (OperationalError tidak tertelan) dan Review Focus 3.

Langkah terakhir dipaksa gagal lewat CHECK ... NOT VALID sementara (INSERT/UPDATE) atau trigger
BEFORE DELETE sementara (DELETE), lalu dicek bahwa semua tabel yang disentuh tidak berubah.
"""
from datetime import datetime

import pytest

from database import get_conn
from fhdb.errors import OperationalError
import modules.beasiswa.service as svc
from modules.beasiswa.service import (
    add_siswa, delete_siswa, add_payment_batch, add_payment_multi, delete_payment_row,
    delete_payment_beasiswa, update_payment_row, add_klaim_multi, delete_klaim_row,
    add_budget_batch, delete_budget_row, update_budget_row, approve_budget_request_batch,
    reject_budget_request_batch, get_budget_list, get_payment_list, get_klaim_list,
    get_sisa_budget,
)

ETF = 2

TABLES = ("siswa", "budget_beasiswa", "budget_beasiswa_requests", "payment_beasiswa",
          "pam_records", "rekam_medis", "klaim_medical", "etf_pa", "etf_pa_lines",
          "app_pa", "sml_pa")


def _snapshot():
    conn = get_conn()
    snap = {t: [dict(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id").fetchall()]
            for t in TABLES}
    conn.close()
    return snap


def _add_check(table, name, expr):
    conn = get_conn()
    conn.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr}) NOT VALID")
    conn.close()


def _drop_check(table, name):
    conn = get_conn()
    conn.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
    conn.close()


def _block_delete(table, where_sql):
    """Trigger BEFORE DELETE sementara yang gagal untuk baris yang memenuhi where_sql (pakai OLD)."""
    conn = get_conn()
    conn.execute(
        "CREATE OR REPLACE FUNCTION t15b_block_delete() RETURNS trigger LANGUAGE plpgsql AS "
        "'BEGIN RAISE EXCEPTION ''t15b: delete diblok''; END'")
    conn.execute(f"CREATE TRIGGER t15b_block BEFORE DELETE ON {table} FOR EACH ROW "
                 f"WHEN ({where_sql}) EXECUTE FUNCTION t15b_block_delete()")
    conn.close()


def _unblock_delete(table):
    conn = get_conn()
    conn.execute(f"DROP TRIGGER IF EXISTS t15b_block ON {table}")
    conn.execute("DROP FUNCTION IF EXISTS t15b_block_delete()")
    conn.close()


def _siswa(code="1250001", nama="Budi Santoso"):
    r = add_siswa(ETF, {"code": code, "nama": nama, "jenjang": "S1", "angkatan": 2025,
                        "program": "SMART", "status": "Aktif"})
    assert r["ok"], r


def _pa_with_lines(n_lines=1, status="open"):
    """etf_pa + n etf_pa_lines untuk siswa 1250001 (harus sudah ada). Return (pa_id, [line_id])."""
    conn = get_conn()
    sid = conn.execute("SELECT id FROM siswa WHERE company_id=? AND code=?", (ETF, "1250001")).fetchone()[0]
    pa_id = conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, tgl_payment_application, status, created_at) "
        "VALUES (?,?,?,?,?)",
        (ETF, "PA/ETF/001/2026", "2026-06-01", status, datetime.now().isoformat(timespec="seconds"))
    ).lastrowid
    lines = []
    for i in range(n_lines):
        lines.append(conn.execute(
            "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) "
            "VALUES (?,?,?,?)", (pa_id, sid, "By Pendidikan", 1000000 * (i + 1))).lastrowid)
    conn.close()
    return pa_id, lines


def _pb_row(**kw):
    row = {"siswa_code": "1250001", "cat1": "By Pendidikan", "cat2": "Semester 1",
           "amount": "3000000", "cat3": "", "cat4": "",
           "tgl_pengajuan": "", "tgl_receive": "", "tgl_pa": "", "tgl_final": ""}
    row.update(kw)
    return row


# --- delete_siswa ------------------------------------------------------------

def test_delete_siswa_atomic_on_failure(app):
    _siswa()
    add_payment_batch(ETF, "1250001", "2026-06-01", "AGRI", "PT X",
                      [{"cat1": "By Pendidikan", "amount": 100}])
    conn = get_conn()
    conn.execute("INSERT INTO budget_beasiswa (company_id, siswa_code, cat1, amount) VALUES (?,?,?,?)",
                 (ETF, "1250001", "By Pendidikan", 500))
    conn.close()
    before = _snapshot()
    _block_delete("siswa", "OLD.code = '1250001'")  # DELETE terakhir (siswa) gagal
    try:
        with pytest.raises(Exception):
            delete_siswa(ETF, "1250001")
    finally:
        _unblock_delete("siswa")
    assert _snapshot() == before
    assert delete_siswa(ETF, "1250001")["ok"] is True
    assert _snapshot()["siswa"] == []


# --- add_payment_batch -------------------------------------------------------

def test_add_payment_batch_atomic_on_failure(app):
    _siswa()
    before = _snapshot()
    _add_check("payment_beasiswa", "t15b_no_999", "amount <> 999")
    try:
        with pytest.raises(Exception):
            add_payment_batch(ETF, "1250001", "2026-06-01", "AGRI", "PT X", [
                {"cat1": "By Pendidikan", "amount": 100},
                {"cat1": "By Tunjangan", "amount": 200},
                {"cat1": "By Tunjangan", "amount": 999},  # INSERT terakhir gagal
            ])
    finally:
        _drop_check("payment_beasiswa", "t15b_no_999")
    assert _snapshot() == before


# --- add_payment_multi -------------------------------------------------------

def test_add_payment_multi_atomic_on_failure(app):
    _siswa()
    pa_id, (line_id,) = _pa_with_lines(1)
    before = _snapshot()
    # Langkah terakhir yang menulis: UPDATE etf_pa SET nomor_pam (setelah pam_records, pb,
    # rekam_medis dan UPDATE status on_process).
    _add_check("etf_pa", "t15b_no_nomor_pam", "nomor_pam IS NULL")
    try:
        result = add_payment_multi(ETF, "ETF", "2026-06-08", "AGRI", "PT. SMART Tbk", [
            _pb_row(amount="1000000", etf_pa_line_id=line_id),
            _pb_row(cat1="By Medical", cat2="Rawat Jalan", amount="500000",
                    rekam_medis={"kelas": "1", "rumah_sakit": "RS", "diagnosa": "Flu",
                                 "spesialisasi": "Umum"}),
        ])
    finally:
        _drop_check("etf_pa", "t15b_no_nomor_pam")
    assert result["ok"] is False
    assert result["pesan"].startswith("Gagal menyimpan payment:")
    assert _snapshot() == before


def test_add_payment_multi_success_writes_everything_in_one_batch(app):
    _siswa()
    pa_id, (line_id,) = _pa_with_lines(1)
    result = add_payment_multi(ETF, "ETF", "2026-06-08", "AGRI", "PT. SMART Tbk", [
        _pb_row(amount="1000000", etf_pa_line_id=line_id),
        _pb_row(cat1="By Medical", cat2="Rawat Jalan", amount="500000",
                rekam_medis={"kelas": "1", "rumah_sakit": "RS", "diagnosa": "Flu",
                             "spesialisasi": "Umum"}),
    ])
    assert result == {"ok": True, "pesan": "2 payment berhasil disimpan (status: open).",
                      "saved": 2, "pam_no": "PAM-001-ETF-06-2026"}
    snap = _snapshot()
    assert [p["pam_no"] for p in snap["pam_records"]] == ["PAM-001-ETF-06-2026"]
    pam = snap["pam_records"][0]
    assert pam["total_amount"] == 1500000.0 and pam["dpp"] == 1500000.0
    assert pam["status"] == "open" and pam["source"] == "beasiswa"
    assert pam["keterangan"] == "Budi Santoso"
    assert {p["pam"] for p in snap["payment_beasiswa"]} == {"PAM-001-ETF-06-2026"}
    medical = [p for p in snap["payment_beasiswa"] if p["cat1"] == "By Medical"][0]
    assert [r["payment_id"] for r in snap["rekam_medis"]] == [medical["id"]]
    assert snap["etf_pa"][0]["status"] == "on_process"
    assert snap["etf_pa"][0]["nomor_pam"] == "PAM-001-ETF-06-2026"


def test_add_payment_multi_reraises_operational_error(app, monkeypatch):
    """R25: outage DB naik ke handler 503, bukan {"ok": False, "pesan": "Gagal menyimpan ..."}."""
    _siswa()

    class _Conn:
        def __init__(self, real):
            self._real = real

        def execute(self, *a, **k):
            return self._real.execute(*a, **k)

        def batch(self, *a, **k):
            raise OperationalError("db down")

        def close(self):
            self._real.close()

    monkeypatch.setattr(svc, "get_conn", lambda: _Conn(get_conn()))
    with pytest.raises(OperationalError):
        add_payment_multi(ETF, "ETF", "2026-06-08", "AGRI", "PT X", [_pb_row()])


# --- penomoran PAM (fn_next_pam_no) ------------------------------------------

def _python_next_pam_no(company_id, code, year, month):
    """Referensi: logika generate_pam_number versi SQLite (scan + max di Python)."""
    import re
    conn = get_conn()
    rows = conn.execute("SELECT pam_no FROM pam_records WHERE company_id=?", (company_id,)).fetchall()
    conn.close()
    pattern = re.compile(rf"PAM-(\d+)-{re.escape(code)}-\d{{2}}-{re.escape(year)}")
    like = re.compile(rf"(?is)^PAM-.*-{re.escape(code)}-.*-{re.escape(year)}$")  # LIKE SQLite
    max_seq = 0
    for r in rows:
        if not like.match(r["pam_no"]):
            continue
        m = pattern.match(r["pam_no"])
        if m:
            max_seq = max(max_seq, int(m.group(1)))
    return f"PAM-{max_seq + 1:03d}-{code}-{month}-{year}"


def _fn_next(company_id, code, year, month):
    conn = get_conn()
    v = conn.execute("SELECT fn_next_pam_no(?, ?, ?, ?)", (company_id, code, year, month)).fetchone()[0]
    conn.close()
    return v


def _seed_pam_nos(company_id, pam_nos):
    conn = get_conn()
    for n in pam_nos:
        conn.execute("INSERT INTO pam_records (company_id, pam_no) VALUES (?,?)", (company_id, n))
    conn.close()


def test_fn_next_pam_no_matches_python_numbering(app):
    assert _fn_next(ETF, "ETF", "2026", "06") == "PAM-001-ETF-06-2026"
    _seed_pam_nos(ETF, [
        "PAM-007-ETF-03-2026",        # bulan lain di tahun sama: ikut (reset hanya per tahun)
        "PAM-002-ETF-06-2026",
        "PAM-050-ETF-01-2025",        # tahun lain: tidak ikut
        "PAM-099-SETF-06-2026",       # kode lain: tidak ikut
        "pam-080-etf-06-2026",        # huruf kecil: lolos LIKE SQLite tapi tidak regex Python
        "PAM-0x9-ETF-06-2026",        # bukan angka
        "PAM-040-ETF-6-2026",         # bulan 1 digit: gagal \d{2}
    ])
    _seed_pam_nos(1, ["PAM-500-ETF-06-2026"])   # company lain: tidak ikut
    for code, year, month in [("ETF", "2026", "06"), ("ETF", "2025", "12"), ("SETF", "2026", "06"),
                              ("ETF", "2027", "01")]:
        assert _fn_next(ETF, code, year, month) == _python_next_pam_no(ETF, code, year, month)
    assert _fn_next(ETF, "ETF", "2026", "06") == "PAM-008-ETF-06-2026"
    _seed_pam_nos(ETF, ["PAM-1234-ETF-02-2026"])  # > 999: tidak dipotong
    assert _fn_next(ETF, "ETF", "2026", "06") == "PAM-1235-ETF-06-2026"
    assert _fn_next(ETF, "ETF", "2026", "06") == _python_next_pam_no(ETF, "ETF", "2026", "06")


def test_fn_next_pam_no_escapes_regex_chars_in_code(app):
    _seed_pam_nos(ETF, ["PAM-004-A.B-05-2026", "PAM-009-AXB-05-2026"])
    assert _fn_next(ETF, "A.B", "2026", "05") == "PAM-005-A.B-05-2026"


def test_add_payment_multi_numbers_follow_existing_pams(app):
    _siswa()
    _seed_pam_nos(ETF, ["PAM-011-ETF-01-2026"])
    r1 = add_payment_multi(ETF, "ETF", "2026-06-08", "AGRI", "PT X", [_pb_row()])
    r2 = add_payment_multi(ETF, "ETF", "2026-07-08", "AGRI", "PT X", [_pb_row()])
    assert (r1["pam_no"], r2["pam_no"]) == ("PAM-012-ETF-06-2026", "PAM-013-ETF-07-2026")


# --- delete_payment_row / delete_payment_beasiswa ----------------------------

def _seed_pa_payment(status="on_process"):
    """Satu PA (on_process) dengan satu payment open yang tertaut PAM + rekam_medis."""
    _siswa()
    pa_id, (line_id,) = _pa_with_lines(1)
    r = add_payment_multi(ETF, "ETF", "2026-06-08", "AGRI", "PT X", [
        _pb_row(cat1="By Medical", cat2="Rawat Inap", amount="700000", etf_pa_line_id=line_id,
                rekam_medis={"kelas": "1", "rumah_sakit": "RS", "diagnosa": "D", "spesialisasi": "S"}),
    ])
    assert r["ok"], r
    conn = get_conn()
    pb_id = conn.execute("SELECT id FROM payment_beasiswa").fetchone()[0]
    conn.close()
    return pa_id, pb_id, r["pam_no"]


@pytest.mark.parametrize("fn", ["delete_payment_row", "delete_payment_beasiswa"])
def test_delete_payment_cascade_success(app, fn):
    pa_id, pb_id, pam_no = _seed_pa_payment()
    if fn == "delete_payment_row":
        result = delete_payment_row(ETF, pb_id)
    else:
        result = delete_payment_beasiswa(pb_id, ETF)
    assert result == {"ok": True, "pesan": "Baris payment dihapus."}
    snap = _snapshot()
    assert snap["payment_beasiswa"] == [] and snap["rekam_medis"] == [] and snap["pam_records"] == []
    assert snap["etf_pa"][0]["status"] == "open" and snap["etf_pa"][0]["nomor_pam"] is None


def test_delete_payment_cascade_keeps_pam_with_remaining_payments(app):
    _siswa()
    r = add_payment_multi(ETF, "ETF", "2026-06-08", "AGRI", "PT X",
                          [_pb_row(amount="100"), _pb_row(amount="200")])
    conn = get_conn()
    ids = [x[0] for x in conn.execute("SELECT id FROM payment_beasiswa ORDER BY id").fetchall()]
    conn.close()
    assert delete_payment_row(ETF, ids[0])["ok"] is True
    snap = _snapshot()
    assert [p["pam_no"] for p in snap["pam_records"]] == [r["pam_no"]]
    assert [p["id"] for p in snap["payment_beasiswa"]] == [ids[1]]


def test_delete_payment_row_atomic_on_failure(app):
    pa_id, pb_id, pam_no = _seed_pa_payment()
    before = _snapshot()
    _add_check("etf_pa", "t15b_no_open", "status <> 'open'")  # UPDATE PA -> open (terakhir) gagal
    try:
        with pytest.raises(Exception):
            delete_payment_row(ETF, pb_id)
    finally:
        _drop_check("etf_pa", "t15b_no_open")
    assert _snapshot() == before


def test_delete_payment_beasiswa_atomic_on_failure(app):
    pa_id, pb_id, pam_no = _seed_pa_payment()
    before = _snapshot()
    _add_check("etf_pa", "t15b_no_open", "status <> 'open'")
    try:
        with pytest.raises(Exception):
            delete_payment_beasiswa(pb_id, ETF)
    finally:
        _drop_check("etf_pa", "t15b_no_open")
    assert _snapshot() == before


# --- update_payment_row ------------------------------------------------------

def test_update_payment_row_atomic_on_failure(app):
    _siswa()
    r1 = add_payment_multi(ETF, "ETF", "2026-06-08", "AGRI", "PT X", [_pb_row()])
    r2 = add_payment_multi(ETF, "ETF", "2026-06-09", "AGRI", "PT X", [_pb_row()])
    conn = get_conn()
    pb_id = conn.execute("SELECT id FROM payment_beasiswa WHERE pam=?", (r1["pam_no"],)).fetchone()[0]
    conn.close()
    before = _snapshot()
    _add_check("pam_records", "t15b_no_boom", "tanggal_bayar IS DISTINCT FROM '1999-01-01'")
    try:
        with pytest.raises(Exception):
            # UPDATE pb.pam lalu UPDATE pam_records.tanggal_bayar (terakhir, gagal)
            update_payment_row(ETF, pb_id, pam=r2["pam_no"], tanggal_bayar="1999-01-01")
    finally:
        _drop_check("pam_records", "t15b_no_boom")
    assert _snapshot() == before


def test_update_payment_row_target_pam_vanished_saves_nothing(app, monkeypatch):
    """Race: PAM target lolos validasi lalu hilang sebelum batch. Dulu rollback() membatalkan
    UPDATE pb.pam; sekarang UPDATE pb bersyarat EXISTS, jadi tidak ada yang tersimpan."""
    _siswa()
    r1 = add_payment_multi(ETF, "ETF", "2026-06-08", "AGRI", "PT X", [_pb_row()])
    r2 = add_payment_multi(ETF, "ETF", "2026-06-09", "AGRI", "PT X", [_pb_row()])
    conn = get_conn()
    pb_id = conn.execute("SELECT id FROM payment_beasiswa WHERE pam=?", (r1["pam_no"],)).fetchone()[0]
    conn.close()

    class _Conn:
        def __init__(self, real):
            self._real = real

        def execute(self, *a, **k):
            return self._real.execute(*a, **k)

        def batch(self, items):
            # hapus PAM target tepat sebelum batch dikirim
            self._real.execute("DELETE FROM pam_records WHERE pam_no=?", (r2["pam_no"],))
            return self._real.batch(items)

        def commit(self):
            pass

        def close(self):
            self._real.close()

    monkeypatch.setattr(svc, "get_conn", lambda: _Conn(get_conn()))
    result = update_payment_row(ETF, pb_id, pam=r2["pam_no"], tanggal_bayar="2026-06-20")
    monkeypatch.undo()
    assert result == {"ok": False, "pesan": "Nomor PAM tidak ditemukan."}
    conn = get_conn()
    assert conn.execute("SELECT pam FROM payment_beasiswa WHERE id=?", (pb_id,)).fetchone()[0] == r1["pam_no"]
    conn.close()


# --- add_klaim_multi / delete_klaim_row --------------------------------------

def _klaim(amount, **kw):
    row = {"siswa_code": "1250001", "tanggal": "2026-01-15", "amount": amount,
           "perawatan": "Rawat Jalan", "kelas": "", "rumah_sakit": "RS", "diagnosa": "D",
           "spesialisasi": "S"}
    row.update(kw)
    return row


def test_add_klaim_multi_links_each_klaim_to_its_payment(app):
    _siswa()
    r = add_klaim_multi(ETF, "PAM-X", "AGRI", "PT X", [_klaim(100), _klaim(200), _klaim(300)])
    assert r == {"ok": True, "pesan": "3 klaim berhasil disimpan.", "saved": 3}
    conn = get_conn()
    pairs = conn.execute(
        "SELECT k.amount, p.amount FROM klaim_medical k JOIN payment_beasiswa p ON p.id = k.payment_id "
        "ORDER BY k.id").fetchall()
    conn.close()
    assert [(a, b) for a, b in pairs] == [(100.0, 100.0), (200.0, 200.0), (300.0, 300.0)]


def test_add_klaim_multi_atomic_on_failure(app):
    _siswa()
    before = _snapshot()
    _add_check("klaim_medical", "t15b_no_999", "amount <> 999")
    try:
        with pytest.raises(Exception):
            add_klaim_multi(ETF, "PAM-X", "AGRI", "PT X", [_klaim(100), _klaim(999)])
    finally:
        _drop_check("klaim_medical", "t15b_no_999")
    assert _snapshot() == before


def test_delete_klaim_row_atomic_on_failure(app):
    _siswa()
    add_klaim_multi(ETF, "PAM-X", "AGRI", "PT X", [_klaim(100)])
    conn = get_conn()
    kid = conn.execute("SELECT id FROM klaim_medical").fetchone()[0]
    conn.close()
    before = _snapshot()
    _block_delete("klaim_medical", "true")  # DELETE klaim_medical (terakhir) gagal
    try:
        with pytest.raises(Exception):
            delete_klaim_row(ETF, kid)
    finally:
        _unblock_delete("klaim_medical")
    assert _snapshot() == before
    assert delete_klaim_row(ETF, kid)["ok"] is True
    snap = _snapshot()
    assert snap["klaim_medical"] == [] and snap["payment_beasiswa"] == []


# --- budget requests ---------------------------------------------------------

def test_add_budget_batch_atomic_on_failure(app):
    _siswa()
    before = _snapshot()
    _add_check("budget_beasiswa_requests", "t15b_no_999", "amount <> 999")
    try:
        with pytest.raises(Exception):
            add_budget_batch(ETF, "1250001", "2026-01-15", "AGRI",
                             [{"cat1": "A", "amount": 1}, {"cat1": "B", "amount": 999}], "fc")
    finally:
        _drop_check("budget_beasiswa_requests", "t15b_no_999")
    assert _snapshot() == before


def _requests():
    conn = get_conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM budget_beasiswa_requests ORDER BY id").fetchall()]
    conn.close()
    return rows


def _seed_requests():
    """budget lama (id 1, 2) + request ADD, EDIT(1), DELETE(2). Return ids request."""
    _siswa()
    conn = get_conn()
    b1 = conn.execute("INSERT INTO budget_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar) "
                      "VALUES (?,?,?,?,?,?,?)", (ETF, "1250001", "By Pendidikan", "S1", "2026-01-01", 100, "AGRI")).lastrowid
    b2 = conn.execute("INSERT INTO budget_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar) "
                      "VALUES (?,?,?,?,?,?,?)", (ETF, "1250001", "By Tunjangan", "S1", "2026-01-01", 200, "AGRI")).lastrowid
    conn.close()
    assert add_budget_batch(ETF, "1250001", "2026-02-01", "AGRI",
                            [{"cat1": "By Medical", "cat2": "X", "amount": 300}], "fc")["ok"]
    assert update_budget_row(ETF, b1, {"cat1": "By Pendidikan", "cat2": "S2", "tanggal": "2026-03-01",
                                       "pillar": "AGRI", "amount": 150}, "fc")["ok"]
    assert delete_budget_row(ETF, b2, "fc")["ok"]
    return [r["id"] for r in _requests()], b1, b2


def test_approve_budget_request_batch_applies_add_edit_delete(app):
    ids, b1, b2 = _seed_requests()
    r = approve_budget_request_batch(ETF, ids + [ids[0]], "bc")  # id ganda diproses sekali
    assert r == {"ok": True, "pesan": "3 baris pengajuan disetujui."}
    snap = _snapshot()
    budget = {b["id"]: b for b in snap["budget_beasiswa"]}
    assert b2 not in budget
    assert budget[b1]["cat2"] == "S2" and budget[b1]["amount"] == 150.0
    added = [b for b in budget.values() if b["cat1"] == "By Medical"]
    assert len(added) == 1 and added[0]["amount"] == 300.0
    assert all(q["status"] == "APPROVED" and q["processed_by"] == "bc" for q in snap["budget_beasiswa_requests"])
    ts = snap["budget_beasiswa_requests"][0]["processed_at"]
    assert isinstance(ts, str) and datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    # approve ulang: sudah APPROVED, tidak ada yang diterapkan lagi
    assert approve_budget_request_batch(ETF, ids, "bc")["pesan"] == "0 baris pengajuan disetujui."
    assert _snapshot()["budget_beasiswa"] == snap["budget_beasiswa"]


def test_approve_budget_request_batch_ignores_other_company(app):
    ids, b1, b2 = _seed_requests()
    before = _snapshot()
    assert approve_budget_request_batch(1, ids, "bc")["pesan"] == "0 baris pengajuan disetujui."
    assert _snapshot() == before


def test_approve_budget_request_batch_atomic_on_failure(app):
    ids, b1, b2 = _seed_requests()
    before = _snapshot()
    # UPDATE status APPROVED untuk request terakhir (langkah terakhir) gagal
    _add_check("budget_beasiswa_requests", "t15b_no_approve_last",
               f"NOT (status = 'APPROVED' AND id = {ids[-1]})")
    try:
        with pytest.raises(Exception):
            approve_budget_request_batch(ETF, ids, "bc")
    finally:
        _drop_check("budget_beasiswa_requests", "t15b_no_approve_last")
    assert _snapshot() == before


def test_reject_budget_request_batch_counts_pending_only(app):
    ids, b1, b2 = _seed_requests()
    approve_budget_request_batch(ETF, [ids[0]], "bc")
    r = reject_budget_request_batch(ETF, ids + [ids[1]], "bc", "kurang dokumen")
    assert r == {"ok": True, "pesan": "2 baris pengajuan ditolak."}
    reqs = _requests()
    assert [q["status"] for q in reqs] == ["APPROVED", "REJECTED", "REJECTED"]
    assert reqs[1]["reject_reason"] == "kurang dokumen"
    assert reject_budget_request_batch(ETF, [], "bc", "x")["pesan"] == "0 baris pengajuan ditolak."


def test_reject_budget_request_batch_atomic_on_failure(app):
    ids, b1, b2 = _seed_requests()
    before = _snapshot()
    _add_check("budget_beasiswa_requests", "t15b_no_reject_last",
               f"NOT (status = 'REJECTED' AND id = {ids[-1]})")
    try:
        with pytest.raises(Exception):
            reject_budget_request_batch(ETF, ids, "bc", "x")
    finally:
        _drop_check("budget_beasiswa_requests", "t15b_no_reject_last")
    assert _snapshot() == before


# --- terjemahan SQL baca -----------------------------------------------------

def test_search_siswa_case_insensitive(client, auth_headers):
    """Review Focus 3: LIKE SQLite case-insensitive -> ILIKE."""
    _siswa(nama="Budi Santoso")
    resp = client.get("/api/v1/siswa?company=ETF&search=budi", headers=auth_headers)
    assert resp.status_code == 200
    assert any(s["nama"] == "Budi Santoso" for s in resp.get_json()["data"])


def test_budget_and_payment_lists_search_case_insensitive_and_totals(app):
    _siswa(nama="Budi Santoso")
    conn = get_conn()
    conn.execute("INSERT INTO budget_beasiswa (company_id, siswa_code, cat1, tanggal, amount, pillar) "
                 "VALUES (?,?,?,?,?,?)", (ETF, "1250001", "By Pendidikan", "2026-03-05", 1000, "AGRI"))
    conn.execute("INSERT INTO budget_beasiswa (company_id, siswa_code, cat1, tanggal, amount, pillar) "
                 "VALUES (?,?,?,?,?,?)", (ETF, "1250001", "By Pendidikan", None, 10, "AGRI"))
    conn.close()
    add_payment_batch(ETF, "1250001", "2026-03-10", "AGRI", "PT X",
                      [{"cat1": "By Pendidikan", "amount": 400}])
    b = get_budget_list(ETF, search="BUDI", bulan="3", tahun="2026")
    assert b["total"] == 1 and b["totals"] == {"By Pendidikan": 1000.0}
    assert b["payment_totals"] == {"By Pendidikan": 400.0}
    all_b = get_budget_list(ETF, search="budi")
    assert all_b["total"] == 2 and all_b["rows"][-1]["tanggal"] is None  # NULL terakhir di DESC
    p = get_payment_list(ETF, search="SANTOSO", bulan="03", tahun="2026")
    assert p["total"] == 1 and p["grand"] == 400.0 and p["budget_totals"] == {"By Pendidikan": 1000.0}
    add_klaim_multi(ETF, "PAM-X", "AGRI", "PT X", [_klaim(250, tanggal="2026-02-01")])
    k = get_klaim_list(ETF, search="budi", bulan="2", tahun="2026")
    assert k["total"] == 1 and k["grand"] == 250.0 and k["rows"][0]["nama"] == "Budi Santoso"


def test_get_sisa_budget_ignores_expired_rows(app):
    _siswa()
    conn = get_conn()
    for amt, exp in ((100, None), (50, "2000-01-01"), (25, "2999-12-31")):
        conn.execute("INSERT INTO budget_beasiswa (company_id, siswa_code, cat1, amount, tgl_expired) "
                     "VALUES (?,?,?,?,?)", (ETF, "1250001", "By Pendidikan", amt, exp))
    conn.close()
    s = get_sisa_budget(ETF, "1250001")
    assert s["total_budget"] == 125.0 and s["sisa"] == {"By Pendidikan": 125.0}
