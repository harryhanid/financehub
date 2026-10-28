# tests/test_etf_pa_atomic.py
# Postgres (Task 11, atomic-flows.md): create_pa / update_pa / delete_pa atomik, penomoran PA dan
# nomor PAM lewat fungsi plpgsql (0004_fn_etf_payment_application.sql), terjemahan filter SQL.
from datetime import datetime

import pytest

from database import get_conn
from modules.etf_payment_application.service import (
    create_pa, update_pa, delete_pa, get_pa_lines, get_pa_flat, get_siswa_autocomplete,
)

COMPANY_ID = 2  # ETF

_LINE = {"jenis_pembayaran": "By Pendidikan", "semester": "Semester 3",
         "tahun_ajaran": "2025/2026", "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000}


@pytest.fixture(autouse=True)
def seed_siswa(clean_db):
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama, jenjang, angkatan, status) VALUES (?,?,?,?,?,?)",
        (COMPANY_ID, "1230001", "Budi Santoso", "S1", 2023, "Aktif"))
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama, jenjang, angkatan, status) VALUES (?,?,?,?,?,?)",
        (COMPANY_ID, "2230001", "Ani Wijaya", "S2", 2023, "Aktif"))
    conn.close()
    yield


def _sid(code):
    conn = get_conn()
    row = conn.execute("SELECT id FROM siswa WHERE code=?", (code,)).fetchone()
    conn.close()
    return row["id"]


def _line(sid, **kw):
    d = dict(_LINE, student_id=sid)
    d.update(kw)
    return d


def _counts(*tables):
    conn = get_conn()
    out = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    conn.close()
    return out


class _TempConstraint:
    """ALTER TABLE ... ADD CONSTRAINT sementara (dibuang di __exit__) untuk memaksa langkah terakhir gagal."""

    def __init__(self, table, name, ddl):
        self.table, self.name, self.ddl = table, name, ddl

    def __enter__(self):
        conn = get_conn()
        conn.execute(f"ALTER TABLE {self.table} ADD CONSTRAINT {self.name} {self.ddl}")
        conn.close()
        return self

    def __exit__(self, *exc):
        conn = get_conn()
        conn.execute(f"ALTER TABLE {self.table} DROP CONSTRAINT IF EXISTS {self.name}")
        conn.close()
        return False


# --- create_pa ---

def test_create_pa_atomic_on_failure():
    from fhdb.errors import IntegrityError
    s1, s2 = _sid("1230001"), _sid("2230001")
    create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [_line(s1)])
    before = _counts("etf_pa", "etf_pa_lines")
    # Line TERAKHIR melanggar CHECK -> header + line pertama harus ikut batal.
    with _TempConstraint("etf_pa_lines", "tmp_t11_no_boom", "CHECK (jenis_pembayaran <> 'BOOM') NOT VALID"):
        with pytest.raises(IntegrityError):
            create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-02"},
                      [_line(s1), _line(s2, jenis_pembayaran="BOOM")])
    assert _counts("etf_pa", "etf_pa_lines") == before
    # Nomor tidak terpakai oleh percobaan gagal: PA berikutnya tetap 002.
    r = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-03"}, [_line(s1)])
    assert r["pa_number"].startswith("PA/ETF/002/")


def test_create_pa_lines_reference_new_header():
    s1, s2 = _sid("1230001"), _sid("2230001")
    r1 = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [_line(s1)])
    r2 = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"},
                   [_line(s1, jumlah_pembayaran=1000), _line(s2, jumlah_pembayaran=2000)])
    assert r2["pa_id"] != r1["pa_id"]
    assert r2["pesan"] == f"Payment Application {r2['pa_number']} berhasil dibuat."
    conn = get_conn()
    rows = conn.execute(
        "SELECT student_id, jumlah_pembayaran, route FROM etf_pa_lines WHERE pa_id=? ORDER BY id",
        (r2["pa_id"],)).fetchall()
    conn.close()
    assert [tuple(r) for r in rows] == [(s1, 1000, "gl"), (s2, 2000, "gl")]


def test_pa_number_counts_per_company_and_table():
    sid = _sid("1230001")
    conn = get_conn()
    # Baris company lain dan tabel PA lain tidak ikut dihitung.
    conn.execute("INSERT INTO etf_pa (company_id, pa_number, status, created_at) VALUES (1,'X','open','2026-01-01')")
    conn.execute("INSERT INTO app_pa (company_id, pa_number, status, created_at) VALUES (?,'Y','open','2026-01-01')",
                 (COMPANY_ID,))
    conn.close()
    year = datetime.now().strftime("%Y")
    r = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [_line(sid)])
    assert r["pa_number"] == f"PA/ETF/001/{year}"
    r = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [_line(sid)], tab="app")
    assert r["pa_number"] == f"PA/APP/002/{year}"


def test_pa_number_function_rejects_unknown_table():
    conn = get_conn()
    with pytest.raises(Exception):
        conn.execute("SELECT fn_etf_pa_next_pa_number('siswa', 2, 'X', '2026')").fetchone()
    conn.close()


# --- update_pa ---

def test_update_pa_nomor_pam_increments_within_month():
    sid = _sid("1230001")
    a = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [_line(sid)])
    b = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [_line(sid)])
    now = datetime.now()
    u1 = update_pa(a["pa_id"], COMPANY_ID, {"status": "on_process"})
    u2 = update_pa(b["pa_id"], COMPANY_ID, {"status": "on_process"})
    assert u1["nomor_pam"] == f"001-ETF-{now:%m}-{now:%Y}"
    assert u2["nomor_pam"] == f"002-ETF-{now:%m}-{now:%Y}"
    assert u1["pesan"] == f"PA pindah ke On Process. Nomor PAM: {u1['nomor_pam']}"
    conn = get_conn()
    stored = conn.execute("SELECT nomor_pam, status FROM etf_pa WHERE id=?", (b["pa_id"],)).fetchone()
    conn.close()
    assert (stored["nomor_pam"], stored["status"]) == (u2["nomor_pam"], "on_process")
    # Sudah punya nomor_pam: tidak dialokasikan ulang.
    u3 = update_pa(a["pa_id"], COMPANY_ID, {"status": "on_process"})
    assert u3["nomor_pam"] == u1["nomor_pam"]
    assert u3["pesan"] == "PA berhasil diupdate."


def test_update_pa_nomor_pam_ignores_other_months():
    sid = _sid("1230001")
    a = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [_line(sid)])
    conn = get_conn()
    # PA lama (created_at bulan lain) yang sudah punya nomor_pam tidak dihitung.
    conn.execute("INSERT INTO etf_pa (company_id, pa_number, nomor_pam, status, created_at) "
                 "VALUES (?,?,?,?,?)", (COMPANY_ID, "OLD", "001-ETF-01-2000", "on_process", "2000-01-15T10:00:00"))
    conn.close()
    now = datetime.now()
    assert update_pa(a["pa_id"], COMPANY_ID, {"status": "on_process"})["nomor_pam"] == f"001-ETF-{now:%m}-{now:%Y}"


def _pa_with_pam(sid, amount=5000000, pam_status="open"):
    r = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [_line(sid, jumlah_pembayaran=amount)])
    line_id = get_pa_lines(r["pa_id"], COMPANY_ID)[0]["id"]
    conn = get_conn()
    conn.execute("INSERT INTO pam_records (company_id, pam_no, total_amount, dpp, status) VALUES (?,?,?,?,?)",
                 (COMPANY_ID, "PAM/T11/1", amount + 1000, amount + 1000, pam_status))
    # pillar wajib: lookup payment dari baris PA difilter pillar tab (id baris PA serial per tabel).
    conn.execute("INSERT INTO payment_beasiswa (company_id, siswa_code, amount, pam, etf_pa_line_id, pillar) "
                 "VALUES (?,?,?,?,?,?)", (COMPANY_ID, "1230001", amount, "PAM/T11/1", line_id, "AGRI"))
    # Baris lain di PAM yang sama (tanpa line PA) ikut dijumlah.
    conn.execute("INSERT INTO payment_beasiswa (company_id, siswa_code, amount, pam) VALUES (?,?,?,?)",
                 (COMPANY_ID, "2230001", 1000, "PAM/T11/1"))
    conn.close()
    return r["pa_id"], line_id


def _pa_state(pa_id, line_id):
    conn = get_conn()
    st = (
        tuple(conn.execute("SELECT status, nomor_pam, keterangan, updated_at FROM etf_pa WHERE id=?",
                           (pa_id,)).fetchone()),
        tuple(conn.execute("SELECT jumlah_pembayaran, semester FROM etf_pa_lines WHERE id=?",
                           (line_id,)).fetchone()),
        tuple(r[0] for r in conn.execute("SELECT amount FROM payment_beasiswa ORDER BY id").fetchall()),
        tuple(conn.execute("SELECT total_amount, dpp FROM pam_records WHERE pam_no='PAM/T11/1'").fetchone()),
    )
    conn.close()
    return st


def test_update_pa_amount_propagates_to_open_pam():
    sid = _sid("1230001")
    pa_id, line_id = _pa_with_pam(sid)
    res = update_pa(pa_id, COMPANY_ID, {"status": "open", "line_id": line_id, "semester": "Semester 4",
                                        "jumlah_pembayaran": 7000000})
    assert res["ok"] is True
    _, line, pb_amounts, pam = _pa_state(pa_id, line_id)
    assert line == (7000000, "Semester 4")
    assert pb_amounts == (7000000, 1000)
    assert pam == (7001000, 7001000)


def test_update_pa_amount_blocked_when_pam_processed():
    sid = _sid("1230001")
    pa_id, line_id = _pa_with_pam(sid, pam_status="on_process")
    before = _pa_state(pa_id, line_id)
    res = update_pa(pa_id, COMPANY_ID, {"line_id": line_id, "jumlah_pembayaran": 7000000})
    assert res["ok"] is False and "PAM/T11/1" in res["pesan"]
    assert _pa_state(pa_id, line_id) == before


def test_update_pa_atomic_on_failure():
    from fhdb.errors import IntegrityError
    sid = _sid("1230001")
    pa_id, line_id = _pa_with_pam(sid)
    before = _pa_state(pa_id, line_id)
    counts = _counts("etf_pa", "etf_pa_lines", "payment_beasiswa", "pam_records")
    # Langkah TERAKHIR (UPDATE total pam_records) gagal -> header (termasuk nomor_pam baru),
    # line dan payment_beasiswa tidak boleh berubah.
    with _TempConstraint("pam_records", "tmp_t11_total", "CHECK (total_amount <> 7001000) NOT VALID"):
        with pytest.raises(IntegrityError):
            update_pa(pa_id, COMPANY_ID, {"status": "on_process", "keterangan": "ubah", "line_id": line_id,
                                          "jumlah_pembayaran": 7000000})
    assert _pa_state(pa_id, line_id) == before
    assert before[0][1] is None  # nomor_pam belum dialokasikan
    assert _counts("etf_pa", "etf_pa_lines", "payment_beasiswa", "pam_records") == counts


# --- delete_pa ---

def test_delete_pa_success_and_blocked_when_linked():
    sid = _sid("1230001")
    r = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [_line(sid), _line(sid)])
    res = delete_pa(r["pa_id"], COMPANY_ID)
    assert res["ok"] is True and r["pa_number"] in res["pesan"]
    assert _counts("etf_pa", "etf_pa_lines") == {"etf_pa": 0, "etf_pa_lines": 0}
    pa_id, _ = _pa_with_pam(sid)
    res = delete_pa(pa_id, COMPANY_ID)
    assert res["ok"] is False and "1 record payment" in res["pesan"]
    assert _counts("etf_pa", "etf_pa_lines") == {"etf_pa": 1, "etf_pa_lines": 1}


def test_delete_pa_atomic_on_failure():
    from fhdb.errors import IntegrityError
    sid = _sid("1230001")
    r = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [_line(sid), _line(sid)])
    before = _counts("etf_pa", "etf_pa_lines")
    conn = get_conn()
    # Tabel sementara yang mereferensikan header: DELETE header (langkah TERAKHIR) melanggar FK,
    # jadi DELETE lines sebelumnya harus ikut batal.
    conn.execute("CREATE TABLE tmp_t11_ref (pa_id bigint REFERENCES etf_pa (id))")
    try:
        conn.execute("INSERT INTO tmp_t11_ref (pa_id) VALUES (?)", (r["pa_id"],))
        with pytest.raises(IntegrityError):
            delete_pa(r["pa_id"], COMPANY_ID)
        assert _counts("etf_pa", "etf_pa_lines") == before
    finally:
        conn.execute("DROP TABLE IF EXISTS tmp_t11_ref")
        conn.close()


# --- terjemahan filter ---

def test_get_pa_flat_filters_translated():
    sid = _sid("1230001")
    r = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [_line(sid)])
    update_pa(r["pa_id"], COMPANY_ID, {"status": "on_process", "tgl_payment_application": "2026-06-01"})
    assert len(get_pa_flat(COMPANY_ID, "agri", bulan_pa="6", tahun_pa="2026", angkatan="2023")) == 1
    assert get_pa_flat(COMPANY_ID, "agri", bulan_pa="7") == []
    assert get_pa_flat(COMPANY_ID, "agri", angkatan="abc") == []
    # Case-insensitive seperti LIKE SQLite.
    assert len(get_pa_flat(COMPANY_ID, "agri", pam="etf", nama="BUDI")) == 1
    assert len(get_siswa_autocomplete(COMPANY_ID, "budi")) == 1


# --- Final fix 3: kunci R51 + guard PAM masih open di update_pa ---

def test_update_pa_takes_r51_lock_first(monkeypatch):
    from fhdb.connection import Connection
    from modules.payment_memo.service import _pb_lock_stmt
    batches = []
    real = Connection.batch

    def spy(self, items):
        items = list(items)
        batches.append(items)
        return real(self, items)
    monkeypatch.setattr(Connection, "batch", spy)
    sid = _sid("1230001")
    pa_id, line_id = _pa_with_pam(sid)
    for data in ({"status": "open", "line_id": line_id, "jumlah_pembayaran": 7000000},
                 {"status": "on_process", "keterangan": "x"}):
        batches.clear()
        assert update_pa(pa_id, COMPANY_ID, data)["ok"] is True
        assert len(batches) == 1
        lock = _pb_lock_stmt(COMPANY_ID)
        assert (batches[0][0][0], tuple(batches[0][0][1])) == (lock[0], tuple(lock[1]))


def test_update_pa_pam_approved_after_precheck_writes_nothing(monkeypatch):
    """PAM masih open saat pre-check, lalu diproses (on_process) sebelum batch: tidak ada yang
    tersimpan (header, line, payment_beasiswa, total PAM) dan pesan sama dengan pre-check."""
    import modules.etf_payment_application.service as etf_svc
    sid = _sid("1230001")
    pa_id, line_id = _pa_with_pam(sid)
    before = _pa_state(pa_id, line_id)

    class _Conn:
        def __init__(self, real):
            self._real = real

        def execute(self, *a, **k):
            return self._real.execute(*a, **k)

        def batch(self, items):
            self._real.execute("UPDATE pam_records SET status='on_process' WHERE pam_no='PAM/T11/1'")
            return self._real.batch(items)

        def close(self):
            self._real.close()

    monkeypatch.setattr(etf_svc, "get_conn", lambda: _Conn(get_conn()))
    res = update_pa(pa_id, COMPANY_ID, {"status": "on_process", "keterangan": "ubah", "line_id": line_id,
                                        "semester": "Semester 9", "jumlah_pembayaran": 7000000})
    monkeypatch.undo()
    assert res["ok"] is False
    assert res["pesan"].startswith("PAM PAM/T11/1 sudah berstatus 'on_process'")
    assert _pa_state(pa_id, line_id) == before
