"""Management Report: raw rows from the modules that feed GL Combine (read-only)."""
from database import get_conn
from modules.general_ledger import service as gl_service
from modules.sponsorship import service as sponsorship_service


def gl_rows(entity: str) -> list:
    """GL SMT / GL ETF rows that carry an amount (see general_ledger.service.load_mr_source)."""
    return gl_service.load_mr_source(entity)


def smt_company_id():
    conn = get_conn()
    try:
        row = conn.execute("SELECT id FROM companies WHERE code = 'SMT'").fetchone()
        return row["id"] if row else None
    finally:
        conn.close()


def sponsor_rows_from(rows: list) -> list:
    """Pure: reduce sponsorship_transaksi rows to what GL Combine needs, ordered by form date then id."""
    ordered = sorted(rows, key=lambda r: (r.get("tanggal_form_sponsor") or "", r.get("id") or 0))
    return [{"tgl": r.get("tanggal_form_sponsor"),
             "perihal": r.get("perihal") or "",
             "amount": float(r.get("amount_request") or 0.0),
             "coa": str(r.get("coa") or "").strip(),
             "cc": str(r.get("cc") or "").strip()} for r in ordered]


def sponsor_rows() -> list:
    """Sponsorship transactions of company SMT, every year, every status."""
    company_id = smt_company_id()
    if company_id is None:
        return []
    return sponsor_rows_from(sponsorship_service.list_transaksi(company_id))
