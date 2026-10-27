# tests/test_etf_pa_budget_lock.py -- Task 6: hapus/edit PA dan budget menghormati kunci budget.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_conn
from modules.etf_payment_application.service import (
    create_pa, delete_pa, update_pa, get_pa_lines, get_pa_flat)
from modules.beasiswa.service import delete_budget_row, update_budget_row
from tests.test_prportal_fn import _siswa, _budget, _payload, _submit

COMPANY_ID = 2  # ETF


def _bstatus(bid):
    conn = get_conn()
    try:
        return conn.execute("SELECT status FROM budget_beasiswa WHERE id=?", (bid,)).fetchone()["status"]
    finally:
        conn.close()


def _seed_pa(amount=1000, jumlah=800):
    """PA PR Portal 1 baris; return (pa_id, pa_number, line_id, budget_id)."""
    _siswa("B1", "Budget Satu")
    _budget("B1", "By Pendidikan", "Semester 1", amount=amount)
    conn = get_conn()
    bid = conn.execute("SELECT id FROM budget_beasiswa WHERE siswa_code='B1'").fetchone()["id"]
    conn.close()
    res = _submit(_payload("B1", [{"budget_id": bid, "tahun_ajaran": "2026/2027", "jumlah": jumlah}]))
    assert res.get("ok") is True, res
    conn = get_conn()
    try:
        row = conn.execute("SELECT p.id AS pa_id, p.pa_number, l.id AS line_id FROM etf_pa p "
                           "JOIN etf_pa_lines l ON l.pa_id=p.id").fetchone()
    finally:
        conn.close()
    return row["pa_id"], row["pa_number"], row["line_id"], bid


def _upd(pa_id, line_id, **kw):
    d = {"tgl_payment_application": "2026-10-27", "status": "open", "klasifikasi": "Normal",
         "line_id": line_id, "jenis_pembayaran": "By Pendidikan", "semester": "Semester 1",
         "tahun_ajaran": "2026/2027", "ipk_sem_sebelumnya": 3.4, "jumlah_pembayaran": 800}
    d.update(kw)
    return update_pa(pa_id, COMPANY_ID, d)


def test_delete_pa_releases_budget():
    pa_id, _, _, bid = _seed_pa()
    assert _bstatus(bid) == "on_progress"
    assert delete_pa(pa_id, COMPANY_ID)["ok"] is True
    assert _bstatus(bid) == "open"


def test_update_line_over_budget_rejected():
    pa_id, _, line_id, _ = _seed_pa()
    res = _upd(pa_id, line_id, jumlah_pembayaran=1001)
    assert res["ok"] is False and res["pesan"].startswith("Jumlah melebihi budget 1")
    assert [l["jumlah_pembayaran"] for l in get_pa_lines(pa_id, COMPANY_ID)] == [800]


def test_update_line_change_category_rejected():
    pa_id, _, line_id, _ = _seed_pa()
    res = _upd(pa_id, line_id, jenis_pembayaran="By Tunjangan")
    assert res == {"ok": False, "pesan": "Jenis Bayar/Semester baris ini terkunci ke budget."}
    res = _upd(pa_id, line_id, semester="Semester 2")
    assert res["ok"] is False and "terkunci" in res["pesan"]
    assert get_pa_lines(pa_id, COMPANY_ID)[0]["jenis_pembayaran"] == "By Pendidikan"


def test_update_line_within_budget_ok():
    pa_id, _, line_id, _ = _seed_pa()
    res = _upd(pa_id, line_id, jumlah_pembayaran=1000)
    assert res["ok"] is True
    l = get_pa_lines(pa_id, COMPANY_ID)[0]
    assert l["jumlah_pembayaran"] == 1000
    assert l["budget_id"] and l["budget_amount"] == 1000


def test_update_line_without_budget_unchanged():
    _siswa("N1", "Tanpa Budget")
    conn = get_conn()
    sid = conn.execute("SELECT id FROM siswa WHERE code='N1'").fetchone()["id"]
    conn.close()
    r = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [
        {"student_id": sid, "jenis_pembayaran": "By Pendidikan", "semester": "Semester 1",
         "tahun_ajaran": "2025/2026", "ipk_sem_sebelumnya": 3.5, "jumlah_pembayaran": 1000}])
    line_id = get_pa_lines(r["pa_id"], COMPANY_ID)[0]["id"]
    res = _upd(r["pa_id"], line_id, jumlah_pembayaran=999999999, jenis_pembayaran="By Medical",
               semester="Semester 9")
    assert res["ok"] is True
    l = get_pa_lines(r["pa_id"], COMPANY_ID)[0]
    assert l["jumlah_pembayaran"] == 999999999 and l["jenis_pembayaran"] == "By Medical"


def test_flat_returns_budget_fields():
    _seed_pa()
    row = get_pa_flat(COMPANY_ID)[0]
    assert row["budget_id"] and row["budget_amount"] == 1000
    assert row["source"] == "prportal" and row["requested_by"] == "harry@sinarmas.test"


def test_delete_budget_in_use_rejected():
    _, pa_number, _, bid = _seed_pa()
    res = delete_budget_row(COMPANY_ID, bid, "tester")
    assert res == {"ok": False, "pesan": f"Budget sedang dipakai PA {pa_number}; tidak bisa dihapus."}
    conn = get_conn()
    conn.execute("UPDATE budget_beasiswa SET status='complete' WHERE id=?", (bid,))
    conn.commit(); conn.close()
    res = delete_budget_row(COMPANY_ID, bid, "tester")
    assert res == {"ok": False, "pesan": "Budget sudah Complete; tidak bisa dihapus."}
    conn = get_conn()
    n = conn.execute("SELECT count(*) AS n FROM budget_beasiswa_requests").fetchone()["n"]
    conn.close()
    assert n == 0


def test_update_budget_amount_below_pa_rejected():
    _, pa_number, _, bid = _seed_pa(amount=1000, jumlah=800)
    res = update_budget_row(COMPANY_ID, bid, {"cat1": "By Pendidikan", "cat2": "Semester 1",
                                              "tanggal": "2026-01-01", "amount": 700}, "tester")
    assert res == {"ok": False, "pesan": f"Amount tidak boleh di bawah jumlah PA {pa_number} (800)."}
    res = update_budget_row(COMPANY_ID, bid, {"cat1": "By Pendidikan", "cat2": "Semester 1",
                                              "tanggal": "2026-01-01", "amount": 900}, "tester")
    assert res["ok"] is True


def test_delete_open_budget_still_requestable():
    _siswa("O1", "Open Satu")
    _budget("O1")
    conn = get_conn()
    bid = conn.execute("SELECT id FROM budget_beasiswa WHERE siswa_code='O1'").fetchone()["id"]
    conn.close()
    assert delete_budget_row(COMPANY_ID, bid, "tester")["ok"] is True


def test_approve_delete_of_in_use_budget_is_noop():
    """Guard atomik saat approve: request DELETE lama untuk budget yang kini dipakai PA tidak menghapus."""
    from modules.beasiswa.service import approve_budget_request_batch
    _, _, _, bid = _seed_pa()
    conn = get_conn()
    rid = conn.execute(
        "INSERT INTO budget_beasiswa_requests (company_id, siswa_code, action_type, budget_id, cat1, cat2, "
        "tanggal, amount, created_by) VALUES (?, 'B1', 'DELETE', ?, 'By Pendidikan', 'Semester 1', "
        "'2026-01-01', 1000, 't') RETURNING id", (COMPANY_ID, bid)).fetchone()["id"]
    conn.commit(); conn.close()
    approve_budget_request_batch(COMPANY_ID, [rid], "bc")
    assert _bstatus(bid) == "on_progress"
