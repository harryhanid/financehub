"""Task 16 (atomic-flows.md, payment_memo bagian 1): alur multi-tulisan PAM harus all-or-nothing di
Postgres, plus penomoran PAM lewat fn_next_pam_no (R24), kunci bersama R51, R23 (update_memo_status),
R25 (OperationalError tidak tertelan) dan Review Focus 3 (pencarian PAM case-insensitive).

Langkah TERAKHIR tiap alur dipaksa gagal lewat CHECK ... NOT VALID sementara (INSERT/UPDATE) atau
trigger BEFORE DELETE sementara (DELETE); lalu dicek bahwa SEMUA tabel yang disentuh tidak berubah.
"""
from datetime import datetime

import pytest

from database import get_conn
from fhdb.errors import OperationalError
import modules.payment_memo.service as svc
from modules.payment_memo.service import (
    create_pam_record, generate_pam_number, get_next_pam_no, upsert_pam_lines, save_klaim_payment,
    save_others_payment, save_smt_pam_transaction, save_pa_payment, create_pam_from_etf_pa,
    delete_payment_beasiswa, cancel_pam_record, reject_pam_record, remove_student_from_pam,
    reject_student_from_pam, update_beasiswa_line_amount, update_pam_and_application,
    set_pam_complete_cascade, mark_beasiswa_lines_complete, realize_advance_payment,
    update_memo_status,
)

ETF = 2

TABLES = ("pam_records", "payment_beasiswa", "klaim_medical", "rekam_medis",
          "pam_transaction_lines", "advance_pam_lines", "smt_pam_lines", "agri_pam_lines",
          "etf_pa", "etf_pa_lines", "app_pa", "sml_pa", "payment_memo", "payment_application",
          "bank_setf")


def _ts():
    return datetime.now().isoformat(timespec="seconds")


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


class _check:
    """with _check(table, expr): CHECK sementara yang membuat tulisan terakhir gagal."""
    def __init__(self, table, expr):
        self.table, self.expr, self.name = table, expr, "t16_force_fail"

    def __enter__(self):
        _add_check(self.table, self.name, self.expr)

    def __exit__(self, *exc):
        _drop_check(self.table, self.name)
        return False


class _block_delete:
    """with _block_delete(table, where): trigger BEFORE DELETE yang gagal untuk baris yang cocok."""
    def __init__(self, table, where_sql):
        self.table, self.where = table, where_sql

    def __enter__(self):
        conn = get_conn()
        conn.execute(
            "CREATE OR REPLACE FUNCTION t16_block_delete() RETURNS trigger LANGUAGE plpgsql AS "
            "'BEGIN RAISE EXCEPTION ''t16: delete diblok''; END'")
        conn.execute(f"CREATE TRIGGER t16_block BEFORE DELETE ON {self.table} FOR EACH ROW "
                     f"WHEN ({self.where}) EXECUTE FUNCTION t16_block_delete()")
        conn.close()

    def __exit__(self, *exc):
        conn = get_conn()
        conn.execute(f"DROP TRIGGER IF EXISTS t16_block ON {self.table}")
        conn.execute("DROP FUNCTION IF EXISTS t16_block_delete()")
        conn.close()
        return False


@pytest.fixture(autouse=True)
def _no_debug_payload_file(monkeypatch, tmp_path):
    """save_klaim_payment menulis ke C:/Financehub/debug_payload.txt (kode lama); alihkan ke tmp_path."""
    import builtins
    real_open = builtins.open

    def _open(path, *a, **kw):
        if str(path).replace("\\", "/").endswith("debug_payload.txt"):
            path = tmp_path / "debug_payload.txt"
        return real_open(path, *a, **kw)
    monkeypatch.setattr(svc, "open", _open, raising=False)


# --- seed helpers -------------------------------------------------------------

def _siswa(code="1250001", nama="Budi Santoso"):
    conn = get_conn()
    sid = conn.execute("INSERT INTO siswa (company_id, code, nama, jenjang) VALUES (?,?,?,?)",
                       (ETF, code, nama, "S1")).lastrowid
    conn.close()
    return sid


def _pa(status="on_process", nomor_pam=None, n_lines=1, sid=None, route=None):
    """etf_pa + n etf_pa_lines. Return (pa_id, [line_id])."""
    sid = sid or _siswa()
    conn = get_conn()
    pa_id = conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, tgl_payment_application, status, nomor_pam, "
        "created_at) VALUES (?,?,?,?,?,?)",
        (ETF, "PA/ETF/001/2026", "2026-06-01", status, nomor_pam, _ts())).lastrowid
    lines = []
    for i in range(n_lines):
        lines.append(conn.execute(
            "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran, route) "
            "VALUES (?,?,?,?,?)", (pa_id, sid, "By Pendidikan", 1_000_000 * (i + 1), route)).lastrowid)
    conn.close()
    return pa_id, lines


def _pam(pam_no="PAM-001-ETF-06-2026", pillar="AGRI", source="beasiswa", status="open", total=0):
    conn = get_conn()
    pam_id = conn.execute(
        "INSERT INTO pam_records (company_id, pam_no, pam_date, total_amount, dpp, pillar, source, "
        "status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (ETF, pam_no, "2026-06-08", total, total, pillar, source, status, _ts())).lastrowid
    conn.close()
    return pam_id


def _pb(pam_no="PAM-001-ETF-06-2026", amount=1_000_000, line_id=None, status="open",
        pillar="AGRI", code="1250001", advance_amount=None, memo_id=None):
    conn = get_conn()
    pb_id = conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, "
        "pam, etf_pa_line_id, status, advance_amount, memo_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (ETF, code, "By Pendidikan", "Semester 1", "2026-06-01", amount, pillar, pam_no, line_id,
         status, advance_amount, memo_id)).lastrowid
    conn.close()
    return pb_id


def _beasiswa_pam(n=2, pa_status="on_process"):
    """PAM beasiswa dengan n payment_beasiswa, masing-masing ke line PA sendiri (1 PA header)."""
    pa_id, lines = _pa(status=pa_status, nomor_pam="PAM-001-ETF-06-2026", n_lines=n)
    pam_id = _pam(total=1_000_000 * n)
    pbs = [_pb(line_id=lid) for lid in lines]
    return pam_id, pa_id, lines, pbs


def _one(sql, params=()):
    conn = get_conn()
    r = conn.execute(sql, params).fetchone()
    conn.close()
    return dict(r) if r else None


# --- create_pam_record + penomoran (R24) -------------------------------------

def test_create_pam_record_atomic_on_failure():
    p1, p2 = _pb(pam_no=None), _pb(pam_no=None)
    before = _snapshot()
    # langkah terakhir: UPDATE payment_beasiswa.pam untuk payment terakhir
    with _check("payment_beasiswa", f"pam IS NULL OR id <> {p2}"):
        conn = get_conn()
        with pytest.raises(Exception):
            create_pam_record(conn, ETF, "ETF", {"pam_date": "2026-06-08", "total_amount": 2_000_000,
                                                 "payment_ids": [p1, p2]})
        conn.close()
    assert _snapshot() == before

    conn = get_conn()
    pam_no = create_pam_record(conn, ETF, "ETF", {"pam_date": "2026-06-08", "total_amount": 2_000_000,
                                                  "payment_ids": [p1, p2]})
    conn.close()
    assert pam_no == "PAM-001-ETF-06-2026"
    rows = _snapshot()
    assert [r["pam"] for r in rows["payment_beasiswa"]] == [pam_no, pam_no]
    pr = rows["pam_records"][0]
    assert (pr["total_amount"], pr["dpp"], pr["ppn"], pr["status"], pr["source"]) == \
        (2_000_000.0, 2_000_000.0, 0.0, "open", "beasiswa")
    assert isinstance(pr["total_amount"], float)


def test_generate_pam_number_preview_matches_allocation_sequence():
    """Pratinjau (get_next_pam_no / generate_pam_number) = nomor yang kemudian dialokasikan."""
    assert generate_pam_number(ETF, "ETF", "2026", "06") == "PAM-001-ETF-06-2026"
    conn = get_conn()
    create_pam_record(conn, ETF, "ETF", {"pam_date": "2026-06-08"})
    create_pam_record(conn, ETF, "ETF", {"pam_date": "2026-07-01"})
    conn.close()
    assert generate_pam_number(ETF, "ETF", "2026", "08") == "PAM-003-ETF-08-2026"
    assert get_next_pam_no(ETF, "ETF", "agri", "2026-09-01") == "PAM-003-ETF-09-2026"
    assert get_next_pam_no(ETF, "ETF", "setf", "2026-09-01") == "PAM-001-SETF-09-2026"
    assert generate_pam_number(ETF, "ETF", "2027", "01") == "PAM-001-ETF-01-2027"


# --- upsert_pam_lines --------------------------------------------------------

def test_upsert_pam_lines_atomic_on_failure():
    pam_id = _pam(pillar="ADVANCE")
    assert upsert_pam_lines(pam_id, "ADVANCE", {"no_vendor": "V-1"}, ETF)["ok"]
    before = _snapshot()
    # langkah terakhir: INSERT smt_pam_lines (konversi advance -> SMT)
    with _check("smt_pam_lines", "tgl_paid IS NULL"):
        with pytest.raises(Exception):
            upsert_pam_lines(pam_id, "ADVANCE", {"nama_vendor": "PT Baru", "tgl_paid": "2026-07-10"}, ETF)
    assert _snapshot() == before

    assert upsert_pam_lines(pam_id, "ADVANCE", {"nama_vendor": "PT Baru", "tgl_paid": "2026-07-10"}, ETF)["ok"]
    snap = _snapshot()
    assert len(snap["advance_pam_lines"]) == 1  # UPDATE, bukan INSERT kedua
    assert snap["advance_pam_lines"][0]["nama_vendor"] == "PT Baru"
    assert snap["advance_pam_lines"][0]["updated_at"] is not None
    assert (snap["pam_records"][0]["pillar"], snap["pam_records"][0]["status"]) == ("SMT", "complete")
    smt = snap["smt_pam_lines"][0]
    # vendor dibaca SETELAH upsert di batch yang sama
    assert (smt["no_vendor"], smt["nama_vendor"], smt["tgl_paid"]) == ("V-1", "PT Baru", "2026-07-10")


def test_upsert_pam_lines_inserts_once_then_updates():
    pam_id = _pam(pillar="AGRI")
    assert upsert_pam_lines(pam_id, "AGRI", {"tgl_proses": "2026-06-10"}, ETF)["ok"]
    assert upsert_pam_lines(pam_id, "AGRI", {"tgl_kirim": "2026-06-11"}, ETF)["ok"]
    rows = _snapshot()["agri_pam_lines"]
    assert len(rows) == 1
    assert (rows[0]["tgl_proses"], rows[0]["tgl_kirim"]) == ("2026-06-10", "2026-06-11")
    assert rows[0]["created_at"] is not None and rows[0]["updated_at"] is not None


# --- save_klaim_payment ------------------------------------------------------

def _klaim_data(pam_no="PAM-009-ETF-06-2026"):
    row = {"siswa_code": "1250001", "cat2": "Rawat Inap", "kelas": "VIP", "rumah_sakit": "RS A",
           "diagnosa": "Demam", "spesialisasi": "Umum", "cat3": "Kamar"}
    return {"tanggal": "2026-06-17", "pam_no": pam_no, "perusahaan": "PT X", "pillar": "AGRI",
            "keterangan": "Klaim", "rows": [dict(row, amount=300), dict(row, amount=200, cat3="Obat")]}


def test_save_klaim_payment_atomic_on_failure():
    before = _snapshot()
    # langkah terakhir: INSERT pam_records
    with _check("pam_records", "source <> 'klaim_medis'"):
        r = save_klaim_payment(ETF, "ETF", _klaim_data())
    assert r["ok"] is False
    assert _snapshot() == before

    r = save_klaim_payment(ETF, "ETF", _klaim_data())
    assert r["ok"] is True, r
    snap = _snapshot()
    pbs, kms = snap["payment_beasiswa"], snap["klaim_medical"]
    assert [p["amount"] for p in pbs] == [300.0, 200.0]
    # pasangan pb -> klaim lewat currval: tiap klaim menunjuk pb-nya sendiri
    assert [k["payment_id"] for k in kms] == [p["id"] for p in pbs]
    assert [k["perawatan"] for k in kms] == ["Kamar", "Obat"]
    assert snap["pam_records"][0]["total_amount"] == 500.0


# --- save_smt_pam_transaction ------------------------------------------------

def _smt_data():
    rows = [{"klasifikasi_sr": "Beasiswa", "dpp": 100, "ppn": 11, "keterangan": "A"},
            {"klasifikasi_sr": "Beasiswa", "dpp": 200, "keterangan": "LAST"}]
    return {"tanggal": "2026-07-06", "pam_no": "PAM-200-SMT-07-2026", "pillar": "SMT", "rows": rows}


def test_save_smt_pam_transaction_atomic_on_failure():
    before = _snapshot()
    # langkah terakhir: INSERT pam_transaction_lines baris terakhir
    with _check("pam_transaction_lines", "keterangan <> 'LAST'"):
        r = save_smt_pam_transaction(1, "SMT", _smt_data())
    assert r["ok"] is False
    assert _snapshot() == before

    assert save_smt_pam_transaction(1, "SMT", _smt_data())["ok"] is True
    snap = _snapshot()
    pam_id = snap["pam_records"][0]["id"]
    assert [l["pam_id"] for l in snap["pam_transaction_lines"]] == [pam_id, pam_id]
    assert snap["pam_records"][0]["total_amount"] == 311.0


# --- save_pa_payment ---------------------------------------------------------

def _pa_rows(lines, medical=False):
    rows = []
    for i, lid in enumerate(lines):
        row = {"siswa_code": "1250001", "cat1": "By Pendidikan", "cat2": "Semester 1",
               "amount": str(1_000_000 * (i + 1)), "etf_pa_line_id": lid}
        if medical and i == 0:
            row.update(cat1="By Medical", cat2="Rawat Inap",
                       rekam_medis={"kelas": "VIP", "rumah_sakit": "RS", "diagnosa": "D",
                                    "spesialisasi": "S"})
        rows.append(row)
    return rows


def test_save_pa_payment_atomic_on_failure():
    pa_id, lines = _pa(status="open", n_lines=2)
    data = {"tab": "agri", "tanggal": "2026-06-08", "pam_no": "PAM-050-ETF-06-2026",
            "perusahaan": "PT. SMART Tbk", "pillar": "AGRI", "rows": _pa_rows(lines, medical=True)}
    before = _snapshot()
    # langkah terakhir: UPDATE etf_pa nomor_pam
    with _check("etf_pa", "nomor_pam IS NULL"):
        r = save_pa_payment(ETF, "ETF", data)
    assert r["ok"] is False
    assert _snapshot() == before

    r = save_pa_payment(ETF, "ETF", data)
    assert r["ok"] is True, r
    snap = _snapshot()
    assert [p["pam"] for p in snap["payment_beasiswa"]] == ["PAM-050-ETF-06-2026"] * 2
    assert snap["rekam_medis"][0]["payment_id"] == snap["payment_beasiswa"][0]["id"]
    assert len(snap["rekam_medis"]) == 1
    pa = snap["etf_pa"][0]
    assert (pa["status"], pa["nomor_pam"]) == ("on_process", "PAM-050-ETF-06-2026")
    assert snap["pam_records"][0]["total_amount"] == 3_000_000.0


def test_save_pa_payment_duplicate_pam_no_saves_nothing():
    _pam(pam_no="PAM-050-ETF-06-2026")
    pa_id, lines = _pa(status="open", n_lines=1)
    before = _snapshot()
    r = save_pa_payment(ETF, "ETF", {"tab": "agri", "tanggal": "2026-06-08",
                                     "pam_no": "PAM-050-ETF-06-2026", "pillar": "AGRI",
                                     "rows": _pa_rows(lines)})
    assert r["ok"] is False
    assert _snapshot() == before


# --- create_pam_from_etf_pa --------------------------------------------------

def test_create_pam_from_etf_pa_atomic_on_failure():
    pa_id, lines = _pa(status="open", n_lines=2)
    before = _snapshot()
    # langkah terakhir: UPDATE etf_pa -> on_process
    with _check("etf_pa", "status <> 'on_process'"):
        with pytest.raises(Exception):
            create_pam_from_etf_pa(ETF, "ETF", "2026-06-08", [pa_id], "ket")
    assert _snapshot() == before

    r = create_pam_from_etf_pa(ETF, "ETF", "2026-06-08", [pa_id], "ket")
    assert r["ok"] is True
    now = datetime.now()
    assert r["pam_no"] == f"PAM-001-ETF-{now:%m}-{now:%Y}"
    snap = _snapshot()
    assert snap["pam_records"][0]["total_amount"] == 3_000_000.0
    assert (snap["etf_pa"][0]["status"], snap["etf_pa"][0]["nomor_pam"]) == ("on_process", r["pam_no"])


# --- delete_payment_beasiswa (payment_memo) ----------------------------------

def test_delete_payment_beasiswa_atomic_on_failure():
    pb_id = _pb()
    conn = get_conn()
    conn.execute("INSERT INTO klaim_medical (company_id, siswa_code, pam, payment_id) VALUES (?,?,?,?)",
                 (ETF, "1250001", "PAM-001-ETF-06-2026", pb_id))
    conn.close()
    before = _snapshot()
    with _block_delete("payment_beasiswa", f"OLD.id = {pb_id}"):  # DELETE terakhir
        with pytest.raises(Exception):
            delete_payment_beasiswa(pb_id, ETF)
    assert _snapshot() == before
    assert delete_payment_beasiswa(pb_id, ETF)["ok"] is True
    snap = _snapshot()
    assert snap["payment_beasiswa"] == [] and snap["klaim_medical"] == []


# --- cancel_pam_record -------------------------------------------------------

def test_cancel_pam_record_atomic_on_failure():
    pam_id, pa_id, lines, pbs = _beasiswa_pam(n=2)
    before = _snapshot()
    # langkah terakhir: UPDATE etf_pa -> open
    with _check("etf_pa", "status <> 'open'"):
        with pytest.raises(Exception):
            cancel_pam_record(pam_id, ETF)
    assert _snapshot() == before

    assert cancel_pam_record(pam_id, ETF)["ok"] is True
    snap = _snapshot()
    assert snap["pam_records"] == [] and snap["payment_beasiswa"] == []
    assert (snap["etf_pa"][0]["status"], snap["etf_pa"][0]["nomor_pam"]) == ("open", None)


def test_cancel_pam_record_etf_agri_atomic_on_failure():
    _pa(status="on_process", nomor_pam="PAM-001-ETF-06-2026")
    pam_id = _pam(source="etf_agri")
    before = _snapshot()
    with _block_delete("pam_records", f"OLD.id = {pam_id}"):  # DELETE terakhir
        with pytest.raises(Exception):
            cancel_pam_record(pam_id, ETF)
    assert _snapshot() == before
    assert cancel_pam_record(pam_id, ETF)["ok"] is True
    assert _snapshot()["etf_pa"][0]["status"] == "open"


# --- reject_pam_record -------------------------------------------------------

def test_reject_pam_record_atomic_on_failure():
    pam_id, pa_id, lines, pbs = _beasiswa_pam(n=2)
    before = _snapshot()
    # langkah terakhir: UPDATE etf_pa -> rejected
    with _check("etf_pa", "status <> 'rejected'"):
        with pytest.raises(Exception):
            reject_pam_record(pam_id, ETF, "salah")
    assert _snapshot() == before

    assert reject_pam_record(pam_id, ETF, "salah")["ok"] is True
    snap = _snapshot()
    assert {p["status"] for p in snap["payment_beasiswa"]} == {"rejected"}
    assert (snap["pam_records"][0]["status"], snap["pam_records"][0]["reject_reason"]) == ("rejected", "salah")
    assert snap["etf_pa"][0]["status"] == "rejected"


def test_reject_pam_record_partial_keeps_header_and_recalculates_total():
    pam_id, pa_id, lines, pbs = _beasiswa_pam(n=2)
    conn = get_conn()
    conn.execute("UPDATE payment_beasiswa SET status='complete', amount=700 WHERE id=?", (pbs[0],))
    conn.close()
    assert reject_pam_record(pam_id, ETF, "x")["ok"] is True
    pr = _one("SELECT status, total_amount, dpp FROM pam_records WHERE id=?", (pam_id,))
    assert pr == {"status": "open", "total_amount": 700.0, "dpp": 700.0}
    assert _one("SELECT status FROM etf_pa WHERE id=?", (pa_id,))["status"] == "on_process"


# --- remove_student_from_pam / reject_student_from_pam ----------------------

def test_remove_student_from_pam_atomic_on_failure():
    pam_id, pa_id, lines, pbs = _beasiswa_pam(n=1)
    before = _snapshot()
    # langkah terakhir: UPDATE etf_pa -> open (setelah DELETE pb + DELETE pam_records kosong)
    with _check("etf_pa", "status <> 'open'"):
        with pytest.raises(Exception):
            remove_student_from_pam(pbs[0], ETF)
    assert _snapshot() == before

    assert remove_student_from_pam(pbs[0], ETF)["ok"] is True
    snap = _snapshot()
    assert snap["payment_beasiswa"] == [] and snap["pam_records"] == []
    assert snap["etf_pa"][0]["status"] == "open"


def test_remove_student_from_pam_recalculates_total_and_keeps_pa():
    pam_id, pa_id, lines, pbs = _beasiswa_pam(n=2)
    assert remove_student_from_pam(pbs[0], ETF)["ok"] is True
    assert _one("SELECT total_amount FROM pam_records WHERE id=?", (pam_id,))["total_amount"] == 1_000_000.0
    assert _one("SELECT status FROM etf_pa WHERE id=?", (pa_id,))["status"] == "on_process"


def test_reject_student_from_pam_atomic_on_failure():
    pam_id, pa_id, lines, pbs = _beasiswa_pam(n=1)
    before = _snapshot()
    # langkah terakhir: UPDATE etf_pa -> rejected
    with _check("etf_pa", "status <> 'rejected'"):
        with pytest.raises(Exception):
            reject_student_from_pam(pbs[0], ETF, "r")
    assert _snapshot() == before

    assert reject_student_from_pam(pbs[0], ETF, "r")["ok"] is True
    snap = _snapshot()
    assert snap["payment_beasiswa"][0]["status"] == "rejected"
    assert snap["pam_records"][0]["status"] == "rejected"
    assert snap["etf_pa"][0]["status"] == "rejected"


# --- update_beasiswa_line_amount ---------------------------------------------

def test_update_beasiswa_line_amount_atomic_on_failure():
    _pam(total=1_000_000)
    pb_id = _pb(amount=1_000_000)
    before = _snapshot()
    # langkah terakhir: UPDATE payment_beasiswa.amount
    with _check("payment_beasiswa", "amount <> 1500000"):
        with pytest.raises(Exception):
            update_beasiswa_line_amount(pb_id, 1_500_000, ETF)
    assert _snapshot() == before

    assert update_beasiswa_line_amount(pb_id, 1_500_000, ETF)["ok"] is True
    assert _one("SELECT total_amount FROM pam_records")["total_amount"] == 1_500_000.0
    assert _one("SELECT amount FROM payment_beasiswa")["amount"] == 1_500_000.0
    # diff 0 -> header tidak disentuh (NULL tetap NULL, seperti `if diff != 0` dulu)
    conn = get_conn()
    conn.execute("UPDATE pam_records SET total_amount=NULL WHERE true")
    conn.close()
    assert update_beasiswa_line_amount(pb_id, 1_500_000, ETF)["ok"] is True
    assert _one("SELECT total_amount FROM pam_records")["total_amount"] is None


# --- update_pam_and_application ----------------------------------------------

def test_update_pam_and_application_atomic_on_failure():
    conn = get_conn()
    memo_id = conn.execute("INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
                           (ETF, "PAM/ETF/2026/001", "open")).lastrowid
    conn.execute("INSERT INTO payment_application (company_id, memo_id, notes) VALUES (?,?,?)",
                 (ETF, memo_id, "lama"))
    conn.close()
    _pa(status="on_process", nomor_pam="PAM-001-ETF-06-2026")
    pam_id = _pam()
    _pb(memo_id=memo_id)
    before = _snapshot()
    # langkah terakhir: UPDATE payment_application.notes
    with _check("payment_application", "notes <> 'baru'"):
        with pytest.raises(Exception):
            update_pam_and_application(pam_id, {"pam_no": "PAM-099-ETF-06-2026", "keterangan": "k"},
                                       {"notes": "baru"}, ETF)
    assert _snapshot() == before

    r = update_pam_and_application(pam_id, {"pam_no": "PAM-099-ETF-06-2026", "keterangan": "k"},
                                   {"notes": "baru"}, ETF)
    assert r["ok"] is True
    snap = _snapshot()
    assert snap["pam_records"][0]["pam_no"] == "PAM-099-ETF-06-2026"
    assert snap["payment_beasiswa"][0]["pam"] == "PAM-099-ETF-06-2026"
    assert snap["etf_pa"][0]["nomor_pam"] == "PAM-099-ETF-06-2026"
    assert snap["payment_application"][0]["notes"] == "baru"


# --- set_pam_complete_cascade ------------------------------------------------

def test_set_pam_complete_cascade_atomic_on_failure():
    pam_id, pa_id, lines, pbs = _beasiswa_pam(n=2)
    before = _snapshot()
    # langkah terakhir: UPDATE etf_pa -> complete
    with _check("etf_pa", "status <> 'complete'"):
        with pytest.raises(Exception):
            set_pam_complete_cascade(pam_id, "2026-07-10", ETF)
    assert _snapshot() == before

    assert set_pam_complete_cascade(pam_id, "2026-07-10", ETF)["ok"] is True
    snap = _snapshot()
    assert snap["pam_records"][0]["status"] == "complete"
    assert {p["status"] for p in snap["payment_beasiswa"]} == {"complete"}
    assert (snap["etf_pa"][0]["status"], snap["etf_pa"][0]["tanggal_bayar"]) == ("complete", "2026-07-10")


# --- mark_beasiswa_lines_complete --------------------------------------------

def test_mark_beasiswa_lines_complete_atomic_on_failure():
    pam_id, pa_id, lines, pbs = _beasiswa_pam(n=2)
    before = _snapshot()
    # langkah terakhir (satu PAM = satu unit): UPDATE pam_records -> partial
    with _check("pam_records", "status <> 'partial'"):
        with pytest.raises(Exception):
            mark_beasiswa_lines_complete([pbs[0]], "2026-07-10", ETF)
    assert _snapshot() == before

    assert mark_beasiswa_lines_complete([pbs[0]], "2026-07-10", ETF)["ok"] is True
    snap = _snapshot()
    assert [p["status"] for p in snap["payment_beasiswa"]] == ["complete", "open"]
    assert snap["pam_records"][0]["status"] == "partial"
    assert snap["etf_pa"][0]["status"] == "partial"

    assert mark_beasiswa_lines_complete([pbs[1]], "2026-07-11", ETF)["ok"] is True
    snap = _snapshot()
    assert (snap["pam_records"][0]["status"], snap["pam_records"][0]["tanggal_bayar"]) == ("complete", "2026-07-11")
    assert (snap["etf_pa"][0]["status"], snap["etf_pa"][0]["tanggal_bayar"]) == ("complete", "2026-07-11")


# --- realize_advance_payment -------------------------------------------------

def test_realize_advance_payment_atomic_on_failure():
    pa_id, lines = _pa(status="paid", nomor_pam="PAM-030-ETF-07-2026", n_lines=1, route="advance")
    _pam(pam_no="PAM-030-ETF-07-2026", pillar="ADVANCE", status="complete", total=3_000_000)
    pb_id = _pb(pam_no="PAM-030-ETF-07-2026", amount=3_000_000, line_id=lines[0], status="paid",
                advance_amount=3_000_000)
    before = _snapshot()
    # langkah terakhir: UPDATE etf_pa -> complete
    with _check("etf_pa", "status <> 'complete'"):
        with pytest.raises(Exception):
            realize_advance_payment(pb_id, 2_500_000, "2026-07-20", ETF)
    assert _snapshot() == before

    r = realize_advance_payment(pb_id, 2_500_000, "2026-07-20", ETF)
    assert r == {"ok": True, "pesan": "Realisasi tersimpan.", "selisih": 500_000.0}
    snap = _snapshot()
    assert snap["payment_beasiswa"][0]["status"] == "complete"
    assert snap["pam_records"][0]["pillar"] == "AGRI"
    assert snap["etf_pa_lines"][0]["jumlah_pembayaran"] == 2_500_000.0
    assert snap["etf_pa"][0]["status"] == "complete"


# --- R23: update_memo_status -------------------------------------------------

def test_update_memo_status_atomic_on_failure():
    """R23: NameError lama (pam_data/current_status/pam_id) tetap ada dan TIDAK ada yang tersimpan."""
    conn = get_conn()
    memo_id = conn.execute("INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
                           (ETF, "PAM/ETF/2026/001", "open")).lastrowid
    conn.close()
    _pb(memo_id=memo_id, status="on_process")
    before = _snapshot()
    with pytest.raises(NameError):
        update_memo_status(memo_id, "complete", "admin", ETF)
    assert _snapshot() == before


# --- R25: OperationalError naik ----------------------------------------------

class _DownConn:
    """Koneksi yang meneruskan bacaan tetapi setiap tulisan (batch / INSERT) gagal seperti outage."""
    def __init__(self, real):
        self._real = real

    def execute(self, sql, *a, **k):
        if sql.lstrip().upper().startswith("INSERT"):
            raise OperationalError("db down")
        return self._real.execute(sql, *a, **k)

    def batch(self, *a, **k):
        raise OperationalError("db down")

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self._real.close()


@pytest.mark.parametrize("call", [
    lambda: save_klaim_payment(ETF, "ETF", _klaim_data()),
    lambda: save_others_payment(ETF, "ETF", {"pam_no": "PAM-1", "keterangan": "k", "dpp": 10}),
    lambda: save_smt_pam_transaction(1, "SMT", _smt_data()),
    lambda: save_pa_payment(ETF, "ETF", {"tab": "agri", "pam_no": "PAM-1", "pillar": "AGRI",
                                         "rows": [{"siswa_code": "1250001", "amount": "10"}]}),
], ids=["save_klaim_payment", "save_others_payment", "save_smt_pam_transaction", "save_pa_payment"])
def test_save_payment_reraises_operational_error(monkeypatch, call):
    monkeypatch.setattr(svc, "get_conn", lambda: _DownConn(get_conn()))
    with pytest.raises(OperationalError):
        call()


# --- Review Focus 3: pencarian PAM case-insensitive --------------------------

def test_search_pam_case_insensitive(client):
    conn = get_conn()
    for no, pt in (("PAM-001-ETF-06-2026", "PT Sinar Abadi"), ("PAM-002-ETF-06-2026", "PT Lain")):
        conn.execute("INSERT INTO pam_records (company_id, pam_no, pam_date, pt, keterangan, status, "
                     "pillar, created_at) VALUES (?,?,?,?,?,?,?,?)",
                     (ETF, no, "2026-06-08", pt, "x", "open", "AGRI", _ts()))
    conn.close()
    client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
    client.post("/select-company", data={"company_id": str(ETF)})
    resp = client.get("/payment-memo/pam?search=sinar")
    assert resp.status_code == 200
    rows = resp.get_json()["rows"]
    assert [r["pt"] for r in rows] == ["PT Sinar Abadi"]
    resp = client.get("/payment-memo/by-pillar/AGRI?search=SINAR")
    assert resp.status_code == 200
    assert [r["pam_no"] for r in resp.get_json()["rows"]] == ["PAM-001-ETF-06-2026"]


# --- R51 / R24: kunci diambil sebagai item batch pertama ---------------------

def _run_behind_lock(pg_dsn, key, fns):
    """Tahan pg_advisory_xact_lock(hashtext(key)) di koneksi terpisah, jalankan tiap fn di thread
    sendiri, tunggu sampai semuanya menunggu kunci itu (pg_locks), lalu lepas: batch berurutan."""
    import threading
    import time
    import psycopg2
    holder = psycopg2.connect(pg_dsn)
    errors = []

    def work(fn):
        try:
            fn()
        except Exception as e:  # pragma: no cover - dilaporkan di bawah
            errors.append(e)
    threads = [threading.Thread(target=work, args=(fn,)) for fn in fns]
    try:
        with holder.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (key,))
        for t in threads:
            t.start()
        deadline = time.time() + 60
        while True:
            with psycopg2.connect(pg_dsn) as probe, probe.cursor() as cur:
                # R53: hanya penunggu kunci INI (bukan seluruh DB). Kunci advisory int8 tercatat
                # sebagai classid (32 bit atas) + objid (32 bit bawah), objsubid = 1.
                cur.execute(
                    "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND NOT granted "
                    "AND objsubid = 1 "
                    "AND objid::bigint = (hashtext(%s)::bigint & 4294967295) "
                    "AND classid::bigint = ((hashtext(%s)::bigint >> 32) & 4294967295)",
                    (key, key))
                waiting = cur.fetchone()[0]
            probe.close()
            if waiting >= len(fns):
                break
            assert time.time() < deadline, f"hanya {waiting} dari {len(fns)} yang menunggu kunci"
            time.sleep(0.05)
    finally:
        holder.rollback()
        holder.close()
        for t in threads:
            t.join(120)
    assert not errors, errors


def test_concurrent_mark_lines_complete_on_same_pam_ends_complete(pg_dsn):
    """Dua user menandai baris berbeda di PAM yang sama: tanpa kunci keduanya bisa melihat saudaranya
    masih open dan sama-sama menulis 'partial'. Dengan kunci R51 yang kedua melihat hasil yang pertama."""
    pam_id, pa_id, lines, pbs = _beasiswa_pam(n=2)
    _run_behind_lock(pg_dsn, f"beasiswa_pb_delete:{ETF}", [
        lambda: mark_beasiswa_lines_complete([pbs[0]], "2026-07-10", ETF),
        lambda: mark_beasiswa_lines_complete([pbs[1]], "2026-07-10", ETF),
    ])
    assert _one("SELECT status FROM pam_records WHERE id=?", (pam_id,))["status"] == "complete"
    assert _one("SELECT status FROM etf_pa WHERE id=?", (pa_id,))["status"] == "complete"


def test_concurrent_create_pam_from_etf_pa_gets_distinct_numbers(pg_dsn):
    sid = _siswa()
    pa1, _ = _pa(status="open", sid=sid)
    pa2, _ = _pa(status="open", sid=sid)
    now = datetime.now()
    # R53: create_pam_from_etf_pa mengambil kunci R51 dulu (lalu kunci pam_no di fn_next_pam_no),
    # jadi kedua thread antre di kunci R51; _run_behind_lock menghitung penunggu kunci itu saja.
    _run_behind_lock(pg_dsn, f"beasiswa_pb_delete:{ETF}", [
        lambda: create_pam_from_etf_pa(ETF, "ETF", "2026-06-08", [pa1]),
        lambda: create_pam_from_etf_pa(ETF, "ETF", "2026-06-08", [pa2]),
    ])
    nos = sorted(r["pam_no"] for r in _snapshot()["pam_records"])
    assert nos == [f"PAM-001-ETF-{now:%m}-{now:%Y}", f"PAM-002-ETF-{now:%m}-{now:%Y}"]


def test_pam_cascades_take_shared_lock_first(monkeypatch):
    """R51: tiap batch alur payment_memo yang menulis payment_beasiswa diawali kunci yang sama dengan
    cascade delete beasiswa."""
    from fhdb.connection import Connection
    batches = []
    real = Connection.batch

    def spy(self, items):
        items = list(items)
        batches.append(items)
        return real(self, items)
    monkeypatch.setattr(Connection, "batch", spy)
    lock = ("SELECT pg_advisory_xact_lock(hashtext(?))", (f"beasiswa_pb_delete:{ETF}",))

    pam_id, pa_id, lines, pbs = _beasiswa_pam(n=3)
    calls = [
        lambda: update_beasiswa_line_amount(pbs[0], 5, ETF),
        lambda: reject_student_from_pam(pbs[1], ETF, "r"),
        lambda: remove_student_from_pam(pbs[2], ETF),
        lambda: update_pam_and_application(pam_id, {"pam_no": "PAM-077-ETF-06-2026"}, {}, ETF),
        lambda: mark_beasiswa_lines_complete([pbs[0]], "2026-07-10", ETF),
        lambda: set_pam_complete_cascade(pam_id, "2026-07-11", ETF),
        lambda: reject_pam_record(pam_id, ETF, "x"),
        lambda: cancel_pam_record(pam_id, ETF),
        lambda: delete_payment_beasiswa(_pb(pam_no=None), ETF),
        lambda: save_klaim_payment(ETF, "ETF", _klaim_data()),
    ]
    for call in calls:
        batches.clear()
        call()
        assert batches, calls.index(call)
        writes_pb = [b for b in batches if any("payment_beasiswa" in sql and not sql.lstrip().upper()
                                               .startswith("SELECT") for sql, _ in b)]
        assert writes_pb, calls.index(call)
        for b in writes_pb:
            assert (b[0][0], tuple(b[0][1])) == lock


# --- R53 (Task 16b) -----------------------------------------------------------

def test_save_others_payment_keeps_decimal_others():
    """R53: pam_records.others double precision -- 1500.5 tidak dibulatkan bigint."""
    r = save_others_payment(ETF, "ETF", {"pam_no": "PAM-300-ETF-06-2026", "keterangan": "k",
                                         "tanggal": "2026-06-08", "dpp": 1000, "ppn": 110.25,
                                         "others": 1500.5})
    assert r["ok"] is True
    pr = _one("SELECT dpp, ppn, others, total_amount FROM pam_records WHERE pam_no=?",
              ("PAM-300-ETF-06-2026",))
    assert pr["others"] == 1500.5
    assert pr["total_amount"] == pr["dpp"] + pr["ppn"] + pr["others"] == 2610.75


def test_save_smt_pam_transaction_keeps_decimal_others():
    data = _smt_data()
    data["rows"][0]["others"] = 0.5
    assert save_smt_pam_transaction(1, "SMT", data)["ok"] is True
    pr = _one("SELECT others, total_amount FROM pam_records WHERE pam_no=?", (data["pam_no"],))
    assert (pr["others"], pr["total_amount"]) == (0.5, 311.5)


def test_create_pam_from_etf_pa_double_submit_creates_one_pam():
    pa_id, _ = _pa(status="open", n_lines=2)
    first = create_pam_from_etf_pa(ETF, "ETF", "2026-06-08", [pa_id], "ket")
    assert first["ok"] is True
    second = create_pam_from_etf_pa(ETF, "ETF", "2026-06-08", [pa_id], "ket")
    assert second == {"ok": False, "pesan": f"PA {[pa_id]} bukan status open."}
    snap = _snapshot()
    assert [p["pam_no"] for p in snap["pam_records"]] == [first["pam_no"]]
    assert snap["etf_pa"][0]["nomor_pam"] == first["pam_no"]


def test_concurrent_create_pam_from_etf_pa_same_pa_creates_one_pam(pg_dsn):
    """Dua submit bersamaan untuk PA yang sama: keduanya lolos validasi 'open' sebelum batch, lalu
    antre di kunci R51. Yang kedua melihat PA sudah on_process dan tidak menulis apa pun."""
    pa_id, _ = _pa(status="open", n_lines=1)
    results = []
    _run_behind_lock(pg_dsn, f"beasiswa_pb_delete:{ETF}", [
        lambda: results.append(create_pam_from_etf_pa(ETF, "ETF", "2026-06-08", [pa_id])),
        lambda: results.append(create_pam_from_etf_pa(ETF, "ETF", "2026-06-08", [pa_id])),
    ])
    assert sorted(r["ok"] for r in results) == [False, True]
    loser = next(r for r in results if not r["ok"])
    assert loser["pesan"] == f"PA {[pa_id]} bukan status open."
    winner = next(r for r in results if r["ok"])
    snap = _snapshot()
    assert [p["pam_no"] for p in snap["pam_records"]] == [winner["pam_no"]]
    assert (snap["etf_pa"][0]["status"], snap["etf_pa"][0]["nomor_pam"]) == ("on_process", winner["pam_no"])


def _rename_before_first_batch(monkeypatch, pam_id, new_no):
    """Simulasikan rename bersamaan (update_pam_and_application di request lain) yang commit
    SETELAH fungsi membaca header tapi SEBELUM batch-nya: header, pb.pam dan etf_pa.nomor_pam."""
    from fhdb.connection import Connection
    real = Connection.batch
    state = {"done": False}

    def spy(self, items):
        if not state["done"]:
            state["done"] = True
            c = get_conn()
            old = c.execute("SELECT pam_no FROM pam_records WHERE id=?", (pam_id,)).fetchone()[0]
            real(c, [
                ("UPDATE payment_beasiswa SET pam=? WHERE pam=?", (new_no, old)),
                ("UPDATE etf_pa SET nomor_pam=? WHERE nomor_pam=?", (new_no, old)),
                ("UPDATE pam_records SET pam_no=? WHERE id=?", (new_no, pam_id)),
            ])
            c.close()
        return real(self, items)
    monkeypatch.setattr(Connection, "batch", spy)


def test_cancel_pam_record_after_concurrent_rename_leaves_no_orphans(monkeypatch):
    pam_id, pa_id, lines, pbs = _beasiswa_pam(n=2)
    _rename_before_first_batch(monkeypatch, pam_id, "PAM-050-ETF-06-2026")
    assert cancel_pam_record(pam_id, ETF)["ok"] is True
    snap = _snapshot()
    assert snap["pam_records"] == [] and snap["payment_beasiswa"] == []
    assert (snap["etf_pa"][0]["status"], snap["etf_pa"][0]["nomor_pam"]) == ("open", None)


def test_cancel_pam_record_etf_agri_after_concurrent_rename(monkeypatch):
    _pa(status="on_process", nomor_pam="PAM-001-ETF-06-2026")
    pam_id = _pam(source="etf_agri")
    _rename_before_first_batch(monkeypatch, pam_id, "PAM-050-ETF-06-2026")
    assert cancel_pam_record(pam_id, ETF)["ok"] is True
    snap = _snapshot()
    assert snap["pam_records"] == []
    assert (snap["etf_pa"][0]["status"], snap["etf_pa"][0]["nomor_pam"]) == ("open", None)


def test_reject_pam_record_after_concurrent_rename_leaves_no_orphans(monkeypatch):
    pam_id, pa_id, lines, pbs = _beasiswa_pam(n=2)
    _rename_before_first_batch(monkeypatch, pam_id, "PAM-050-ETF-06-2026")
    assert reject_pam_record(pam_id, ETF, "salah")["ok"] is True
    snap = _snapshot()
    assert {(p["pam"], p["status"]) for p in snap["payment_beasiswa"]} == {("PAM-050-ETF-06-2026", "rejected")}
    assert snap["pam_records"][0]["status"] == "rejected"
    assert snap["etf_pa"][0]["status"] == "rejected"


def test_set_pam_complete_cascade_after_concurrent_rename_completes_lines(monkeypatch):
    pam_id, pa_id, lines, pbs = _beasiswa_pam(n=2)
    _rename_before_first_batch(monkeypatch, pam_id, "PAM-050-ETF-06-2026")
    assert set_pam_complete_cascade(pam_id, "2026-07-10", ETF)["ok"] is True
    snap = _snapshot()
    assert snap["pam_records"][0]["status"] == "complete"
    assert {(p["pam"], p["status"]) for p in snap["payment_beasiswa"]} == {("PAM-050-ETF-06-2026", "complete")}
    assert (snap["etf_pa"][0]["status"], snap["etf_pa"][0]["tanggal_bayar"]) == ("complete", "2026-07-10")


def test_update_pam_and_application_after_concurrent_rename_leaves_no_orphans(monkeypatch):
    conn = get_conn()
    memo_id = conn.execute("INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
                           (ETF, "PAM/ETF/2026/001", "open")).lastrowid
    conn.execute("INSERT INTO payment_application (company_id, memo_id, notes) VALUES (?,?,?)",
                 (ETF, memo_id, "lama"))
    conn.close()
    _pa(status="on_process", nomor_pam="PAM-001-ETF-06-2026")
    pam_id = _pam()
    _pb(memo_id=memo_id)
    _rename_before_first_batch(monkeypatch, pam_id, "PAM-050-ETF-06-2026")
    r = update_pam_and_application(pam_id, {"pam_no": "PAM-099-ETF-06-2026"}, {"notes": "baru"}, ETF)
    assert r["ok"] is True
    snap = _snapshot()
    assert snap["pam_records"][0]["pam_no"] == "PAM-099-ETF-06-2026"
    assert snap["payment_beasiswa"][0]["pam"] == "PAM-099-ETF-06-2026"
    assert snap["etf_pa"][0]["nomor_pam"] == "PAM-099-ETF-06-2026"
    assert snap["payment_application"][0]["notes"] == "baru"


@pytest.mark.parametrize("code", ["A-B", "A.B"])
def test_memo_number_with_regex_special_company_code(code):
    """fn_next_memo_no: karakter non-[A-Za-z0-9_] di kode di-escape (bukan backreference invalid),
    dan 'A.B' tidak ikut menghitung nomor 'AXB'."""
    from modules.payment_memo.service import generate_memo_number
    assert generate_memo_number(ETF, code, "2026") == f"PAM/{code}/2026/001"
    conn = get_conn()
    for no in (f"PAM/{code}/2026/004", "PAM/AXB/2026/009"):
        conn.execute("INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
                     (ETF, no, "open"))
    conn.close()
    assert generate_memo_number(ETF, code, "2026") == f"PAM/{code}/2026/005"
