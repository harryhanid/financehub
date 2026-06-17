# tests/test_import_pam.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime
import pytest

# akan diimport setelah Task 2
from tmp_import_excel import (
    match_pam_agri, match_open_pam, normalize_date, normalize_amount
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _pam_db(pam_no, pam_date, total, status, id_):
    return {"id": id_, "pam_no": pam_no, "pam_date": pam_date,
            "total_amount": float(total), "status": status, "tanggal_bayar": None}


def _pam_ex(pam_no, pam_date, total, status, tgl_paid=None):
    return {"PAM No": pam_no, "PAM Date": pam_date, "Total (Rp)": total,
            "Status": status, "Tgl Paid": tgl_paid}


def _pb_db(id_, code, cat1, cat2, tanggal, amount,
           pam="", perusahaan="", status="open"):
    return {"id": id_, "siswa_code": code, "cat1": cat1, "cat2": cat2,
            "tanggal": tanggal, "amount": float(amount),
            "pam": pam, "perusahaan": perusahaan, "status": status}


def _pb_ex(code, cat1, cat2, tanggal, amount,
           pam="", perusahaan="", status="open"):
    return {"Code": code, "Kategori 1": cat1, "Kategori 2": cat2,
            "Tanggal": tanggal, "Amount (Rp)": amount,
            "PAM No": pam, "Perusahaan": perusahaan, "Status": status}


# ── normalize_date ─────────────────────────────────────────────────────────────

def test_normalize_date_string():
    assert normalize_date("2026-06-15") == "2026-06-15"

def test_normalize_date_datetime():
    assert normalize_date(datetime(2026, 6, 15, 10, 30)) == "2026-06-15"

def test_normalize_date_none():
    assert normalize_date(None) is None

def test_normalize_date_long_string():
    assert normalize_date("2026-06-15 00:00:00") == "2026-06-15"

def test_normalize_date_empty_string():
    assert normalize_date("") is None


# ── normalize_amount ───────────────────────────────────────────────────────────

def test_normalize_amount_none():
    assert normalize_amount(None) == 0.0

def test_normalize_amount_int():
    assert normalize_amount(1_000_000) == 1_000_000.0

def test_normalize_amount_invalid_string():
    assert normalize_amount("not a number") == 0.0


# ── match_pam_agri ─────────────────────────────────────────────────────────────

def test_match_pam_agri_update_status():
    """Row sama PAM No, status berubah on_process → complete + tgl_paid diisi."""
    db = [_pam_db("PAM-001-ETF-06-2026", "2026-06-15", 1_000_000, "on_process", 1)]
    ex = [_pam_ex("PAM-001-ETF-06-2026", "2026-06-15", 1_000_000, "complete", "2026-06-17")]
    r = match_pam_agri(ex, db)
    assert len(r["updates"]) == 1
    assert r["updates"][0][1]["Status"] == "complete"
    assert r["updates"][0][1]["Tgl Paid"] == "2026-06-17"
    assert r["renames"] == []
    assert r["deletes"] == []
    assert r["skips"]   == []

def test_match_pam_agri_no_change():
    """Tidak ada field yang berubah → tidak masuk updates."""
    db = [_pam_db("PAM-001-ETF-06-2026", "2026-06-15", 1_000_000, "on_process", 1)]
    ex = [_pam_ex("PAM-001-ETF-06-2026", "2026-06-15", 1_000_000, "on_process")]
    r = match_pam_agri(ex, db)
    assert r["updates"] == []
    assert r["deletes"] == []
    assert r["renames"] == []
    assert r["skips"]   == []

def test_match_pam_agri_delete():
    """Row ada di DB tapi tidak ada di Excel → DELETE."""
    db = [_pam_db("PAM-001-ETF-06-2026", "2026-06-15", 1_000_000, "on_process", 1)]
    ex = []
    r = match_pam_agri(ex, db)
    assert len(r["deletes"]) == 1
    assert r["deletes"][0]["pam_no"] == "PAM-001-ETF-06-2026"
    assert r["updates"] == []

def test_match_pam_agri_rename():
    """PAM No lama diganti di Excel, tapi pam_date + total_amount sama → auto-RENAME."""
    db = [_pam_db("PAM-001-AGRI-06-2026", "2026-06-15", 1_000_000, "on_process", 1)]
    ex = [_pam_ex("PAM-001-ETF-06-2026",  "2026-06-15", 1_000_000, "on_process")]
    r = match_pam_agri(ex, db)
    assert len(r["renames"]) == 1
    assert r["renames"][0][0]["pam_no"] == "PAM-001-AGRI-06-2026"
    assert r["renames"][0][1]["PAM No"] == "PAM-001-ETF-06-2026"
    assert r["deletes"] == []
    assert r["skips"]   == []

def test_match_pam_agri_skip_ambiguous():
    """Dua DB rows dengan pam_date + total sama → tidak bisa auto-detect → SKIP."""
    db = [
        _pam_db("PAM-001-AGRI-06-2026", "2026-06-15", 1_000_000, "on_process", 1),
        _pam_db("PAM-002-AGRI-06-2026", "2026-06-15", 1_000_000, "on_process", 2),
    ]
    ex = [_pam_ex("PAM-NEW-ETF-06-2026", "2026-06-15", 1_000_000, "on_process")]
    r = match_pam_agri(ex, db)
    assert len(r["skips"])   == 1
    assert len(r["deletes"]) == 2


# ── match_open_pam ─────────────────────────────────────────────────────────────

def test_match_open_pam_update():
    """Composite key cocok, pam + perusahaan + status berubah → UPDATE."""
    db = [_pb_db(1, "2250234", "By Tunjangan", "Semester 2", "2026-06-15", 19_433_500)]
    ex = [_pb_ex("2250234", "By Tunjangan", "Semester 2", "2026-06-15", 19_433_500,
                 pam="PAM-057-ETF-06-2026", perusahaan="PT. SMART Tbk", status="on_process")]
    r = match_open_pam(ex, db)
    assert len(r["updates"]) == 1
    assert r["updates"][0][1]["PAM No"] == "PAM-057-ETF-06-2026"
    assert r["deletes"] == []
    assert r["skips"]   == []

def test_match_open_pam_no_change():
    """Composite key cocok, semua field sama → tidak ada update."""
    db = [_pb_db(1, "2250234", "By Tunjangan", "Semester 2", "2026-06-15", 19_433_500,
                 pam="PAM-056", perusahaan="PT. SMART", status="open")]
    ex = [_pb_ex("2250234", "By Tunjangan", "Semester 2", "2026-06-15", 19_433_500,
                 pam="PAM-056", perusahaan="PT. SMART", status="open")]
    r = match_open_pam(ex, db)
    assert r["updates"] == []
    assert r["deletes"] == []
    assert r["skips"]   == []

def test_match_open_pam_delete():
    """Row ada di DB tapi dihapus dari Excel → DELETE."""
    db = [_pb_db(1, "2250234", "By Tunjangan", "Semester 2", "2026-06-15", 19_433_500)]
    ex = []
    r = match_open_pam(ex, db)
    assert len(r["deletes"]) == 1
    assert r["deletes"][0]["siswa_code"] == "2250234"

def test_match_open_pam_skip():
    """Row di Excel tidak ada match di DB → SKIP + warning."""
    db = []
    ex = [_pb_ex("9999999", "By Tunjangan", "Semester 2", "2026-06-15", 5_000_000)]
    r = match_open_pam(ex, db)
    assert len(r["skips"]) == 1
    assert r["updates"] == []
    assert r["deletes"] == []
