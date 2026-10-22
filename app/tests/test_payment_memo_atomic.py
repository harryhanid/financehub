"""Task 17 (atomic-flows.md, payment_memo bagian 2): alur memo/draft multi-tulisan harus all-or-nothing
di Postgres, penomoran memo lewat fn_next_memo_no, kunci bersama R51, R25 untuk routes.py
(_handle_pam_attachment_upload dan ipay_next_pam_no), R48/R50 untuk export Excel, dan pencarian
fiori/sml/energy yang case-insensitive seperti LIKE SQLite.

Langkah TERAKHIR tiap alur dipaksa gagal lewat CHECK ... NOT VALID sementara; lalu dicek bahwa SEMUA
tabel yang disentuh tidak berubah. Helper diambil dari test Task 16 (tests/test_pam_atomic.py) lewat
import modul (bukan `from ... import`, supaya test di sana tidak ikut terkumpul dua kali).
"""
import io
from datetime import datetime

import openpyxl
import pytest

import tests.test_pam_atomic as t16
from database import get_conn
from fhdb.errors import OperationalError
import modules.payment_memo.service as svc
from modules.payment_memo.service import (
    create_memo, generate_memo_number, set_memo_tanggal_bayar, update_draft_and_linked,
    get_fiori_list, get_sml_list, get_energy_list,
)

ETF = 2
_snapshot, _check, _pb, _pa, _one = t16._snapshot, t16._check, t16._pb, t16._pa, t16._one

TABLES = t16.TABLES + ("payment_memo_items", "setf_pa", "setf_pa_lines")


def _snap():
    conn = get_conn()
    snap = {t: [dict(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id").fetchall()]
            for t in TABLES}
    conn.close()
    return snap


def _items(*pb_ids):
    return [{"source_id": pid, "source_module": "beasiswa", "description": f"d{pid}",
             "amount": 1_000_000, "vendor": "Budi", "bank_account": "BCA 1"} for pid in pb_ids]


# --- create_memo + penomoran memo ---------------------------------------------

def test_create_memo_atomic_on_failure():
    pb1, pb2 = _pb(pam_no=None), _pb(pam_no=None)
    before = _snap()
    # Tulisan terakhir = UPDATE payment_beasiswa untuk item kedua.
    with _check("payment_beasiswa", f"id <> {pb2} OR status <> 'on_process'"):
        res = create_memo(ETF, "ETF", "2025-06-10", "n", "admin", _items(pb1, pb2))
    assert res["ok"] is False
    assert _snap() == before

    res = create_memo(ETF, "ETF", "2025-06-10", "n", "admin", _items(pb1, pb2))
    assert res["ok"] is True and res["memo_number"] == "PAM/ETF/2025/001"
    memo = _one("SELECT * FROM payment_memo WHERE id=?", (res["memo_id"],))
    assert memo["memo_number"] == "PAM/ETF/2025/001" and memo["total_amount"] == 2_000_000.0
    conn = get_conn()
    items = [dict(r) for r in conn.execute(
        "SELECT * FROM payment_memo_items WHERE memo_id=? ORDER BY id", (res["memo_id"],))]
    pbs = [dict(r) for r in conn.execute(
        "SELECT status, memo_id FROM payment_beasiswa ORDER BY id")]
    conn.close()
    assert [i["source_id"] for i in items] == [pb1, pb2]
    assert pbs == [{"status": "on_process", "memo_id": res["memo_id"]}] * 2


def test_create_memo_number_matches_preview_and_continues_sequence():
    conn = get_conn()
    conn.execute("INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
                 (ETF, "PAM/ETF/2025/009", "open"))
    # Tidak cocok regex (kode lain / tahun lain / company lain): tidak dihitung.
    conn.execute("INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
                 (ETF, "PAM/SMT/2025/050", "open"))
    conn.execute("INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
                 (1, "PAM/ETF/2025/070", "open"))
    conn.close()
    assert generate_memo_number(ETF, "ETF", "2025") == "PAM/ETF/2025/010"
    res = create_memo(ETF, "ETF", "2025-01-02", "", "admin", _items(_pb(pam_no=None)))
    assert res["memo_number"] == "PAM/ETF/2025/010"
    assert generate_memo_number(ETF, "ETF", "2025") == "PAM/ETF/2025/011"


def test_concurrent_create_memo_gets_distinct_numbers(pg_dsn):
    pb1, pb2 = _pb(pam_no=None), _pb(pam_no=None)
    t16._run_behind_lock(pg_dsn, "memo_number:ETF:2025", [
        lambda: create_memo(ETF, "ETF", "2025-06-10", "", "a", _items(pb1)),
        lambda: create_memo(ETF, "ETF", "2025-06-10", "", "b", _items(pb2)),
    ])
    nos = sorted(r["memo_number"] for r in _snap()["payment_memo"])
    assert nos == ["PAM/ETF/2025/001", "PAM/ETF/2025/002"]


def test_create_memo_reraises_operational_error(monkeypatch):
    monkeypatch.setattr(svc, "get_conn", lambda: t16._DownConn(get_conn()))
    with pytest.raises(OperationalError):
        create_memo(ETF, "ETF", "2025-06-10", "", "admin", _items(_pb(pam_no=None)))


# --- set_memo_tanggal_bayar ---------------------------------------------------

def _memo_with_lines():
    """Memo + pb yang tertaut ke etf_pa_lines id L dan (id kembar, perilaku lama) setf_pa_lines id L."""
    conn = get_conn()
    memo_id = conn.execute("INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
                           (ETF, "PAM/ETF/2026/001", "on_process")).lastrowid
    conn.close()
    sid = t16._siswa()
    pa_id, (line_id,) = _pa(status="on_process", sid=sid)
    conn = get_conn()
    setf_id = conn.execute("INSERT INTO setf_pa (company_id, pa_number, status, created_at) "
                           "VALUES (?,?,?,?)", (ETF, "PA/SETF/001", "on_process", t16._ts())).lastrowid
    setf_line = conn.execute("INSERT INTO setf_pa_lines (id, pa_id, student_id) VALUES (?,?,?)",
                             (line_id, setf_id, sid)).lastrowid
    conn.close()
    assert setf_line == line_id
    pb = _pb(pam_no=None, line_id=line_id, status="on_process", memo_id=memo_id)
    return memo_id, pa_id, setf_id, pb


def test_set_memo_tanggal_bayar_atomic_on_failure():
    memo_id, pa_id, setf_id, pb = _memo_with_lines()
    before = _snap()
    # Tulisan terakhir = UPDATE setf_pa (tabel ke-5 di loop PA).
    with _check("setf_pa", "status <> 'complete'"):
        with pytest.raises(Exception):
            set_memo_tanggal_bayar(memo_id, "2026-07-01", ETF)
    assert _snap() == before

    assert set_memo_tanggal_bayar(memo_id, "2026-07-01", ETF)["ok"] is True
    assert _one("SELECT status, tanggal_bayar FROM payment_memo WHERE id=?", (memo_id,)) == \
        {"status": "complete", "tanggal_bayar": "2026-07-01"}
    assert _one("SELECT status FROM payment_beasiswa WHERE id=?", (pb,))["status"] == "complete"
    for tbl, pid in (("etf_pa", pa_id), ("setf_pa", setf_id)):
        assert _one(f"SELECT status, tanggal_bayar FROM {tbl} WHERE id=?", (pid,)) == \
            {"status": "complete", "tanggal_bayar": "2026-07-01"}


def test_set_memo_tanggal_bayar_without_lines_only_updates_memo():
    conn = get_conn()
    memo_id = conn.execute("INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
                           (ETF, "PAM/ETF/2026/002", "on_process")).lastrowid
    conn.close()
    pa_id, _ = _pa(status="on_process")
    assert set_memo_tanggal_bayar(memo_id, "2026-07-02", ETF)["ok"] is True
    assert _one("SELECT status FROM etf_pa WHERE id=?", (pa_id,))["status"] == "on_process"


# --- update_draft_and_linked ----------------------------------------------------

def _draft():
    conn = get_conn()
    memo_id = conn.execute("INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
                           (ETF, "PAM/ETF/2026/003", "open")).lastrowid
    conn.execute("INSERT INTO payment_application (company_id, memo_id, status, notes) VALUES (?,?,?,?)",
                 (ETF, memo_id, "draft", "lama"))
    conn.close()
    pam_id = t16._pam(total=1_000_000)
    pb = _pb(memo_id=memo_id)
    return pb, pam_id, memo_id


def test_update_draft_and_linked_atomic_on_failure():
    pb, pam_id, memo_id = _draft()
    before = _snap()
    # Tulisan terakhir = UPDATE payment_application.
    with _check("payment_application", "notes <> 'baru'"):
        with pytest.raises(Exception):
            update_draft_and_linked(pb, {"amount": 2_000_000}, {"keterangan": "ket baru"},
                                    {"notes": "baru"}, ETF)
    assert _snap() == before

    res = update_draft_and_linked(pb, {"amount": 2_000_000}, {"keterangan": "ket baru"},
                                  {"notes": "baru"}, ETF)
    assert res["ok"] is True
    assert _one("SELECT amount FROM payment_beasiswa WHERE id=?", (pb,))["amount"] == 2_000_000.0
    assert _one("SELECT keterangan FROM pam_records WHERE id=?", (pam_id,))["keterangan"] == "ket baru"
    assert _one("SELECT notes FROM payment_application WHERE memo_id=?", (memo_id,))["notes"] == "baru"


def test_memo_flows_take_shared_lock_first(monkeypatch):
    """R51: batch yang menulis payment_beasiswa diawali kunci beasiswa_pb_delete:<company_id>."""
    from fhdb.connection import Connection
    batches = []
    real = Connection.batch

    def spy(self, items):
        items = list(items)
        batches.append(items)
        return real(self, items)
    monkeypatch.setattr(Connection, "batch", spy)
    lock = ("SELECT pg_advisory_xact_lock(hashtext(?))", (f"beasiswa_pb_delete:{ETF}",))

    memo_id, _, _, _ = _memo_with_lines()
    pb, _, _ = _draft()
    calls = [
        lambda: create_memo(ETF, "ETF", "2025-06-10", "", "admin", _items(_pb(pam_no=None))),
        lambda: set_memo_tanggal_bayar(memo_id, "2026-07-01", ETF),
        lambda: update_draft_and_linked(pb, {"amount": 5}, {}, {}, ETF),
    ]
    for i, call in enumerate(calls):
        batches.clear()
        call()
        assert len(batches) == 1, i
        assert (batches[0][0][0], tuple(batches[0][0][1])) == lock, i


# --- R25: routes.py ------------------------------------------------------------

def _login_etf(client):
    client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
    client.post("/select-company", data={"company_id": str(ETF)})


@pytest.fixture
def fake_drive(monkeypatch):
    import utils.gdrive_service as gd
    monkeypatch.setattr(gd, "create_gdrive_folder", lambda name: "folder-1")
    ids = iter(["file-A", "file-B", "file-C"])
    monkeypatch.setattr(gd, "upload_file_to_gdrive", lambda f, name, mime, folder: next(ids))


def _post_others_with_file(client, monkeypatch, pam_no):
    import modules.payment_memo.routes as routes
    monkeypatch.setattr(routes, "save_others_payment",
                        lambda cid, code, data: {"ok": True, "pam_no": pam_no, "pesan": "ok"})
    return client.post("/payment-memo/ipay/save-others",
                       data={"data": "{}", "file": (io.BytesIO(b"x"), "a.pdf")},
                       content_type="multipart/form-data")


def test_pam_attachment_upload_appends_file_ids(client, monkeypatch, fake_drive):
    pam_id = t16._pam()
    conn = get_conn()
    conn.execute("UPDATE pam_records SET attachment_file_id='old-1' WHERE id=?", (pam_id,))
    conn.close()
    _login_etf(client)
    resp = _post_others_with_file(client, monkeypatch, "PAM-001-ETF-06-2026")
    assert resp.status_code == 200 and resp.get_json()["ok"] is True
    assert "gagal" not in resp.get_json()["pesan"]
    assert _one("SELECT attachment_file_id FROM pam_records WHERE id=?", (pam_id,)) == \
        {"attachment_file_id": "old-1,file-A"}

    other = t16._pam(pam_no="PAM-002-ETF-06-2026")
    resp = _post_others_with_file(client, monkeypatch, "PAM-002-ETF-06-2026")
    assert resp.status_code == 200
    assert _one("SELECT attachment_file_id FROM pam_records WHERE id=?", (other,)) == \
        {"attachment_file_id": "file-B"}


def test_pam_attachment_upload_db_outage_returns_503(client, monkeypatch, fake_drive):
    """routes.py:71 dulu menelan outage dan menjawab ok:true walau tautan lampiran hilang."""
    t16._pam()
    _login_etf(client)
    import database

    class _DownOnUpdate(t16._DownConn):
        def execute(self, sql, *a, **k):
            if sql.lstrip().upper().startswith("UPDATE PAM_RECORDS"):
                raise OperationalError("db down")
            return self._real.execute(sql, *a, **k)
    monkeypatch.setattr(database, "get_conn", lambda: _DownOnUpdate(get_conn()))
    resp = _post_others_with_file(client, monkeypatch, "PAM-001-ETF-06-2026")
    assert resp.status_code == 503


def test_pam_attachment_upload_drive_error_still_reported_in_message(client, monkeypatch):
    import utils.gdrive_service as gd

    def boom(name):
        raise RuntimeError("drive mati")
    monkeypatch.setattr(gd, "create_gdrive_folder", boom)
    t16._pam()
    _login_etf(client)
    resp = _post_others_with_file(client, monkeypatch, "PAM-001-ETF-06-2026")
    assert resp.status_code == 200
    assert "(Upload GDrive gagal: drive mati)" in resp.get_json()["pesan"]


def test_ipay_next_pam_no_db_outage_returns_503(client, monkeypatch):
    import modules.payment_memo.routes as routes

    def down(*a, **k):
        raise OperationalError("db down")
    monkeypatch.setattr(routes, "get_next_pam_no", down)
    _login_etf(client)
    resp = client.get("/payment-memo/ipay/next-pam-no?tab=agri&date=2026-06-01")
    assert resp.status_code == 503


# --- Excel export (R48/R50) dan pencarian fiori/sml/energy ----------------------

def test_export_pam_tab_keeps_float_and_text_cells():
    from modules.payment_memo.exports import export_pam_tab_excel
    conn = get_conn()
    conn.execute(
        "INSERT INTO pam_records (company_id, pam_no, pam_date, total_amount, due_date, status, source, "
        "created_at) VALUES (?,?,?,?,?,?,?,?)",
        (ETF, "PAM-001-ETF-05-2026", "2026-05-01", 2_000_000.5, "2026-06-01", "open", "etf_agri",
         "2026-05-01T10:00:00"))
    conn.close()
    from modules.payment_memo.service import get_pam_list
    assert isinstance(get_pam_list(ETF)[0]["total_amount"], float)
    ws = openpyxl.load_workbook(io.BytesIO(export_pam_tab_excel(ETF, bulan="05", tahun="2026",
                                                                source="agri"))).active
    row = [c.value for c in ws[2]]
    assert row[0] == "PAM-001-ETF-05-2026" and row[1] == "2026-05-01"
    assert row[7] == 2_000_000.5                               # double precision -> float (SQLite REAL)
    assert row[8] == "2026-06-01"


def test_fiori_sml_energy_search_case_insensitive():
    conn = get_conn()
    conn.execute("INSERT INTO fiori_pa (no_pa, nama_vendor, terima_document) VALUES (?,?,?)",
                 ("PA-APP-001", "PT Vendor ABC", "2026-05-10"))
    conn.execute("INSERT INTO fiori_pa (no_pa, nama_vendor, terima_document) VALUES (?,?,?)",
                 ("PA-APP-002", "PT Lain", None))
    for tbl in ("sml_pa", "energy_pa"):
        conn.execute(f"INSERT INTO {tbl} (company_id, pa_number, no_pa, nama_vendor, terima_document, "
                     f"created_at) VALUES (?,?,?,?,?,?)",
                     (ETF, f"{tbl}-1", "X-1", "PT Vendor ABC", "2026-05-10", t16._ts()))
    conn.close()
    assert [r["no_pa"] for r in get_fiori_list("vendor abc")] == ["PA-APP-001"]
    assert [r["no_pa"] for r in get_sml_list("VENDOR")] == ["X-1"]
    assert [r["no_pa"] for r in get_energy_list("vendor abc")] == ["X-1"]
    # NULL terima_document di akhir untuk DESC (urutan SQLite).
    assert [r["no_pa"] for r in get_fiori_list()] == ["PA-APP-001", "PA-APP-002"]
