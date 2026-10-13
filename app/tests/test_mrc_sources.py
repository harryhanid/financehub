from database import get_conn
from modules.general_ledger import service as gl_service
from modules.management_report import combine_sources as src
from tests.test_gl_sync import mkrow

LOG = dict(synced_by="u", filename="f", content_hash="h", rows_before=0, rows_after=1,
           total_debit=0, total_credit=0, dropped=0, summary={})


def insert_sponsor(company_id, tgl, perihal, amount, coa="701078002", cc="POSPON"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO sponsorship_transaksi (company_id, cat, description, tanggal_form_sponsor, cat1, cat2, "
        "cat3, lembaga_perorangan, perihal, amount_request, coa, cc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (company_id, "Event", "desc", tgl, "c1", "c2", "APP", "lembaga", perihal, amount, coa, cc))
    conn.commit()
    conn.close()


def test_smt_company_id_is_looked_up_by_code():
    conn = get_conn()
    expected = conn.execute("SELECT id FROM companies WHERE code='SMT'").fetchone()["id"]
    conn.close()
    assert src.smt_company_id() == expected


def test_sponsor_rows_only_smt_ordered_by_form_date_then_id():
    smt = src.smt_company_id()
    conn = get_conn()
    other = conn.execute("SELECT id FROM companies WHERE code != 'SMT' LIMIT 1").fetchone()["id"]
    conn.close()
    insert_sponsor(smt, "2026-02-10", "B", 20.0)
    insert_sponsor(smt, "2026-01-05", "A2", 10.0)
    insert_sponsor(smt, "2026-01-05", "A1", 5.0)          # same date: id order
    insert_sponsor(other, "2026-01-01", "ETF row", 99.0)  # other company: excluded
    rows = src.sponsor_rows()
    assert [(r["tgl"], r["perihal"], r["amount"]) for r in rows] == [
        ("2026-01-05", "A2", 10.0), ("2026-01-05", "A1", 5.0), ("2026-02-10", "B", 20.0)]
    assert rows[0]["coa"] == "701078002" and rows[0]["cc"] == "POSPON"


def test_sponsor_rows_include_every_year():
    smt = src.smt_company_id()
    insert_sponsor(smt, "2025-12-31", "old", 1.0)
    insert_sponsor(smt, "2026-01-01", "new", 2.0)
    assert [r["perihal"] for r in src.sponsor_rows()] == ["old", "new"]


def test_sponsor_rows_from_handles_null_perihal_and_amount():
    out = src.sponsor_rows_from([
        {"id": 1, "tanggal_form_sponsor": "2026-01-01", "perihal": None, "amount_request": None,
         "coa": None, "cc": None}])
    assert out == [{"tgl": "2026-01-01", "perihal": "", "amount": 0.0, "coa": "", "cc": ""}]


def test_sponsor_rows_empty_when_smt_company_is_missing(monkeypatch):
    monkeypatch.setattr(src, "smt_company_id", lambda: None)
    assert src.sponsor_rows() == []


def test_gl_rows_delegates_to_the_general_ledger_service():
    gl_service.replace_all("smt", [mkrow(acc_management="6-1810", debit_credit=5.0,
                                         allocation_memo="m", job_name="J")], LOG)
    rows = src.gl_rows("smt")
    assert len(rows) == 1 and rows[0]["acc_management"] == "6-1810" and rows[0]["id_no"] == "GJ-1"
