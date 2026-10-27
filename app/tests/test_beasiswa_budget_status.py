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
