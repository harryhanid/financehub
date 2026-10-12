# tests/test_gl_parser.py
import pytest

from modules.general_ledger import parser as p

HEADER = ["", "x", "x1", "Account\nStatutory", "Description Account \nStatutory",
          "Account\nManagement", "Description Account \nManagement", "ID#", "Date", "Memo",
          "Debit", "Credit", "Job Name", "Job Description", "PPH/Non PPH", "Budget Activity",
          "Customer/ Vendor", "Allocation Memo", "EVENT", "Qty Awal", "Qty Akhir", "UOM",
          "Nama Item", "Harga Satuan", "Keterangan 1", "Keterangan 2"]


def raw(**kw):
    """One raw sheet row aligned to HEADER; unspecified cells are None."""
    pos = {"entry_no": 1, "source_type": 2, "acc_statutory": 3, "acc_statutory_desc": 4,
           "acc_management": 5, "acc_management_desc": 6, "id_no": 7, "tgl": 8, "memo": 9,
           "debit": 10, "credit": 11, "job_name": 12, "job_desc": 13, "budget_activity": 15,
           "customer_vendor": 16, "allocation_memo": 17, "event": 18, "qty_awal": 19,
           "qty_akhir": 20, "uom": 21, "nama_item": 22, "harga_satuan": 23, "ket1": 24,
           "ket2": 25}
    r = [None] * len(HEADER)
    for k, v in kw.items():
        r[pos[k]] = v
    return r


def test_maps_columns_and_converts_values():
    res = p.normalise_rows(HEADER, [raw(
        entry_no=1.0, source_type="GJ - Acrue", acc_statutory="2-1110",
        acc_statutory_desc="Other Payables", acc_management="2-1110", id_no="GJ-00168",
        tgl=46023.0, memo="Reversal", debit=918367069.0, credit=0.0, job_name="POCFAD",
        customer_vendor="Bank Sinarmas", ket1="k1")])
    assert res.dropped == 0 and len(res.rows) == 1
    r = res.rows[0]
    assert set(r) == set(p.COLUMNS)
    assert r["entry_no"] == 1 and r["source_type"] == "GJ - Acrue"
    assert r["acc_statutory"] == "2-1110" and r["id_no"] == "GJ-00168"
    assert r["tgl"] == "2026-01-01"          # Excel serial 46023
    assert r["debit"] == 918367069.0 and r["credit"] == 0.0
    assert r["ket1"] == "k1" and r["ket2"] == ""


def test_missing_cells_become_zero_and_empty_text():
    r = p.normalise_rows(HEADER, [raw(acc_statutory="1-1", id_no="X-1", tgl=46023.0)]).rows[0]
    assert r["debit"] == 0.0 and r["credit"] == 0.0 and r["memo"] == ""


def test_formula_only_rows_are_dropped_and_counted():
    junk = raw(entry_no=3.0, acc_statutory="", acc_management=0.0, memo="Sumbangan - 00 Jan 1900")
    good = raw(acc_statutory="1-1", id_no="X-1", tgl=46023.0, debit=5.0)
    blank = [None] * len(HEADER)
    res = p.normalise_rows(HEADER, [junk, good, blank])
    assert len(res.rows) == 1 and res.dropped == 1        # fully blank rows are not counted


def test_excel_error_cells_are_ignored():
    r = p.normalise_rows(HEADER, [raw(acc_statutory="1-1", id_no="X-1", tgl=46023.0,
                                      debit="0x2A", memo="0x07", ket1="ok")]).rows[0]
    assert r["debit"] == 0.0 and r["memo"] == "" and r["ket1"] == "ok"


def test_text_date_is_kept_and_zero_date_is_none():
    a = p.normalise_rows(HEADER, [raw(acc_statutory="1-1", tgl="2026-02-03")]).rows[0]
    b = p.normalise_rows(HEADER, [raw(acc_statutory="1-1", tgl=0.0)]).rows[0]
    assert a["tgl"] == "2026-02-03" and b["tgl"] is None


def test_missing_required_header_raises():
    bad = [h for h in HEADER if h != "Debit"]
    with pytest.raises(p.ParseError, match="Debit"):
        p.normalise_rows(bad, [])
