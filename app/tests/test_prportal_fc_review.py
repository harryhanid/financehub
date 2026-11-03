# tests/test_prportal_fc_review.py -- PA PR Portal berstatus On Review FC: Approve -> open + Checked Fincon, Reject -> rejected + budget kembali open
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_conn
from modules.etf_payment_application.service import (
    approve_pa_fc, reject_pa_fc, update_pa, bulk_update_pa, delete_pa, get_pa_flat,
)
from tests.test_prportal_fn import _siswa, _budget, _payload, _submit, _today

COMPANY_ID = 2


def _make(code="F1"):
    _siswa(code, "FC " + code)
    _budget(code, "By Pendidikan", "Semester 1", amount=5_000_000)
    conn = get_conn()
    bid = conn.execute("SELECT id FROM budget_beasiswa WHERE siswa_code=?", (code,)).fetchone()["id"]
    conn.close()
    res = _submit(_payload(code, [{"budget_id": bid, "tahun_ajaran": "2026/2027", "jumlah": 4_000_000}]))
    assert res["ok"] is True, res
    return res["pa_id"], bid


def _pa(pa_id):
    conn = get_conn()
    try:
        return conn.execute("SELECT status, checked_by_fincon, reject_reason FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    finally:
        conn.close()


def _budget_status(bid):
    conn = get_conn()
    try:
        return conn.execute("SELECT status FROM budget_beasiswa WHERE id=?", (bid,)).fetchone()["status"]
    finally:
        conn.close()


def test_approve_sets_open_and_checked_fincon_today():
    pa_id, bid = _make("F1")
    assert _pa(pa_id)["status"] == "on_review_fc"
    out = approve_pa_fc(pa_id, COMPANY_ID, "agri")
    assert out["ok"] is True, out
    pa = _pa(pa_id)
    assert pa["status"] == "open" and pa["checked_by_fincon"] == _today()
    assert _budget_status(bid) == "on_progress"   # tetap terkunci sampai dibayar


def test_approve_twice_is_refused():
    pa_id, _ = _make("F2")
    assert approve_pa_fc(pa_id, COMPANY_ID, "agri")["ok"] is True
    assert approve_pa_fc(pa_id, COMPANY_ID, "agri")["ok"] is False


def test_reject_releases_budget_and_reuse_then_delete_is_safe():
    pa_id, bid = _make("F3")
    assert reject_pa_fc(pa_id, COMPANY_ID, "", "agri")["ok"] is False          # alasan wajib
    assert _pa(pa_id)["status"] == "on_review_fc"
    out = reject_pa_fc(pa_id, COMPANY_ID, "Dokumen kurang", "agri")
    assert out["ok"] is True, out
    pa = _pa(pa_id)
    assert pa["status"] == "rejected" and pa["reject_reason"] == "Dokumen kurang"
    assert _budget_status(bid) == "open"
    conn = get_conn()
    n = conn.execute("SELECT count(*) AS n FROM etf_pa_lines WHERE pa_id=? AND budget_id IS NOT NULL", (pa_id,)).fetchone()["n"]
    conn.close()
    assert n == 0
    # budget dipakai PA baru; menghapus PA yang ditolak tidak boleh membuka budget itu lagi
    res2 = _submit(_payload("F3", [{"budget_id": bid, "tahun_ajaran": "2026/2027", "jumlah": 1_000_000}]))
    assert res2["ok"] is True, res2
    assert delete_pa(pa_id, COMPANY_ID, "agri")["ok"] is True
    assert _budget_status(bid) == "on_progress"
    assert reject_pa_fc(pa_id, COMPANY_ID, "lagi", "agri")["ok"] is False


def test_reject_after_approve_is_refused_and_keeps_budget():
    pa_id, bid = _make("F4")
    assert approve_pa_fc(pa_id, COMPANY_ID, "agri")["ok"] is True
    assert reject_pa_fc(pa_id, COMPANY_ID, "x", "agri")["ok"] is False
    assert _pa(pa_id)["status"] == "open" and _budget_status(bid) == "on_progress"


def test_edit_and_bulk_cannot_bypass_review():
    pa_id, _ = _make("F5")
    update_pa(pa_id, COMPANY_ID, {"status": "open", "checked_by_fincon": "2026-01-01"}, "agri")
    pa = _pa(pa_id)
    assert pa["status"] == "on_review_fc" and not pa["checked_by_fincon"]
    bulk_update_pa([pa_id], "status", "open", COMPANY_ID, "agri")
    bulk_update_pa([pa_id], "checked_by_fincon", "2026-01-01", COMPANY_ID, "agri")
    pa = _pa(pa_id)
    assert pa["status"] == "on_review_fc" and not pa["checked_by_fincon"]


def test_active_filter_includes_on_review_fc():
    pa_id, _ = _make("F6")
    ids = [r["pa_id"] for r in get_pa_flat(COMPANY_ID, "agri", "active")]
    assert pa_id in ids
    ids = [r["pa_id"] for r in get_pa_flat(COMPANY_ID, "agri", "on_review_fc")]
    assert pa_id in ids
