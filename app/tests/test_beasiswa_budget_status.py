# tests/test_beasiswa_budget_status.py -- Task 7: status budget di Data Budget + badge PA PR Portal.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_conn
from modules.beasiswa.service import get_budget_list, set_budget_status
from tests.test_prportal_fn import _siswa, _budget
from tests.test_etf_pa_budget_lock import _seed_pa, _bstatus

COMPANY_ID = 2


def _bid(code):
    conn = get_conn()
    try:
        return conn.execute("SELECT id FROM budget_beasiswa WHERE siswa_code=? ORDER BY id LIMIT 1",
                            (code,)).fetchone()["id"]
    finally:
        conn.close()


def _login(client, username="admin", password="Admin@123"):
    client.post("/auth/login", json={"username": username, "password": password})
    client.post("/select-company", data={"company_id": "2"})


def test_budget_list_includes_effective_status():
    _siswa("S1", "Aktif Satu")
    _siswa("S2", "Lulus Dua", status="Lulus")
    _budget("S1")
    _budget("S2")
    rows = {r["siswa_code"]: r for r in get_budget_list(COMPANY_ID)["rows"]}
    assert rows["S1"]["status"] == "open"
    assert rows["S2"]["status"] == "non_aktif"
    assert rows["S1"]["status_label"] == "Open"
    assert rows["S2"]["status_label"] == "Non Aktif"


def test_budget_list_filter_status():
    _siswa("S1", "Aktif Satu")
    _siswa("S2", "Lulus Dua", status="Lulus")
    _siswa("S3", "Aktif Tiga")
    _budget("S1")
    _budget("S2")
    _budget("S3", status="complete")
    codes = lambda st: sorted(r["siswa_code"] for r in get_budget_list(COMPANY_ID, status=st)["rows"])
    assert codes("open") == ["S1"]
    assert codes("non_aktif") == ["S2"]
    assert codes("complete") == ["S3"]
    assert codes("") == ["S1", "S2", "S3"]


def test_set_budget_status_requires_fin_admin(client):
    import bcrypt
    pw = bcrypt.hashpw(b"Req@12345", bcrypt.gensalt(4)).decode()
    conn = get_conn()
    conn.execute("INSERT INTO users (username, password_hash, role, must_change_pw) "
                 "VALUES (?, ?, 'requester', 0)", ("req1", pw))
    conn.commit()
    conn.close()
    _siswa("S1", "Aktif Satu")
    _budget("S1")
    bid = _bid("S1")
    _login(client, "req1", "Req@12345")
    r = client.post(f"/beasiswa/budget/{bid}/status", json={"status": "complete"})
    assert r.status_code == 403
    assert _bstatus(bid) == "open"


def test_set_budget_status_rejects_open_when_used_by_pa():
    pa_id, pa_number, _, bid = _seed_pa()
    res = set_budget_status(COMPANY_ID, bid, "open")
    assert res == {"ok": False, "pesan": f"Budget dipakai PA {pa_number}; hapus PA dulu."}
    assert _bstatus(bid) == "on_progress"


def test_set_budget_status_ok(client):
    _siswa("S1", "Aktif Satu")
    _budget("S1")
    bid = _bid("S1")
    _login(client)
    r = client.post(f"/beasiswa/budget/{bid}/status", json={"status": "complete"})
    assert r.status_code == 200 and r.get_json()["ok"] is True
    assert _bstatus(bid) == "complete"
    r = client.post(f"/beasiswa/budget/{bid}/status", json={"status": "open"})
    assert r.get_json()["ok"] is True and _bstatus(bid) == "open"
    r = client.post(f"/beasiswa/budget/{bid}/status", json={"status": "bogus"})
    assert r.get_json()["ok"] is False
    assert set_budget_status(COMPANY_ID, 999999, "open")["ok"] is False


def test_pages_render_new_markers(client):
    _login(client)
    r = client.get("/beasiswa/")
    assert r.status_code == 200 and b"bgt-list-status" in r.data
    r = client.get("/etf-payment-application/")
    assert r.status_code == 200 and b"badge-prportal" in r.data


def _seed_mixed():
    _siswa("S1", "Aktif Satu")
    _siswa("S2", "Lulus Dua", status="Lulus")
    _siswa("S3", "Aktif Tiga")
    _budget("S1")
    _budget("S2")
    _budget("S3", status="complete")


def test_export_csv_respects_status_filter(client):
    _seed_mixed()
    _login(client)
    body = client.get("/beasiswa/budget/export/csv?status=complete").data.decode("utf-8-sig")
    assert "S3" in body and "S1" not in body and "S2" not in body
    assert "Status" in body.splitlines()[0] and "Complete" in body
    body = client.get("/beasiswa/budget/export/csv?status=non_aktif").data.decode("utf-8-sig")
    assert "S2" in body and "S1" not in body and "S3" not in body and "Non Aktif" in body


def test_export_xlsx_respects_status_filter(client):
    import io, openpyxl
    _seed_mixed()
    _login(client)
    r = client.get("/beasiswa/budget/export/xlsx?status=complete")
    assert r.status_code == 200
    ws = openpyxl.load_workbook(io.BytesIO(r.data)).active
    hdr = [c.value for c in ws[6]]
    assert hdr[-1] == "Status"
    codes = [ws.cell(row=i, column=2).value for i in range(7, ws.max_row + 1)]
    assert [c for c in codes if c] == ["S3"]
    assert ws.cell(row=7, column=11).value == "Complete"


def test_export_pdf_with_status_filter_ok(client):
    _seed_mixed()
    _login(client)
    r = client.get("/beasiswa/budget/export/pdf?status=open")
    assert r.status_code == 200 and r.data[:4] == b"%PDF"


def test_set_budget_status_fin_role_ok(client):
    import bcrypt
    pw = bcrypt.hashpw(b"Fin@12345", bcrypt.gensalt(4)).decode()
    conn = get_conn()
    conn.execute("INSERT INTO users (username, password_hash, role, must_change_pw) "
                 "VALUES (?, ?, 'Fin', 0)", ("fin1", pw))
    conn.commit()
    conn.close()
    _siswa("S1", "Aktif Satu")
    _budget("S1")
    bid = _bid("S1")
    _login(client, "fin1", "Fin@12345")
    r = client.post(f"/beasiswa/budget/{bid}/status", json={"status": "complete"})
    assert r.status_code == 200 and r.get_json()["ok"] is True
    assert _bstatus(bid) == "complete"


def test_set_budget_status_locks_budget_row_first_in_same_batch(monkeypatch):
    """Review akhir F2: SELECT ... FOR UPDATE pada baris budget mendahului UPDATE bersyarat, satu batch."""
    import modules.beasiswa.service as svc
    _siswa("L1", "Lock Satu")
    _budget("L1")
    bid = _bid("L1")
    seen = []
    real_get_conn = svc.get_conn

    def spy_conn():
        conn = real_get_conn()
        real_batch = conn.batch

        def batch(items):
            items = list(items)
            seen.append([sql for sql, _ in items])
            return real_batch(items)
        conn.batch = batch
        return conn
    monkeypatch.setattr(svc, "get_conn", spy_conn)
    assert set_budget_status(COMPANY_ID, bid, "complete")["ok"] is True
    assert len(seen) == 1 and len(seen[0]) == 2
    assert seen[0][0].startswith("SELECT id FROM budget_beasiswa") and seen[0][0].endswith("FOR UPDATE")
    assert seen[0][1].startswith("UPDATE budget_beasiswa SET status=?")
    assert _bstatus(bid) == "complete"
