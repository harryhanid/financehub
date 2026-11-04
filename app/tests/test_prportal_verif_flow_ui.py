# tests/test_prportal_verif_flow_ui.py -- kolom PA Verified PO Fin dan riwayat serah terima di halaman Payment Application Flow.
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_conn
from modules.etf_payment_application.service import (
    approve_pa_fc, bulk_update_pa, export_pa_excel, get_pa_flat, update_pa,
)
from tests.test_prportal_fc_review import _make
from tests.test_prportal_serah import _call, _ready, OWNER

COMPANY_ID = 2
TEMPLATE = os.path.join(os.path.dirname(__file__), "..", "templates", "etf_payment_application", "index.html")


def _login(client):
    client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
    client.post("/select-company", data={"company_id": str(COMPANY_ID)})


def _verified(pa_id):
    conn = get_conn()
    try:
        return conn.execute("SELECT pa_verified_by_po_fin AS v FROM etf_pa WHERE id=?", (pa_id,)).fetchone()["v"]
    finally:
        conn.close()


def test_flat_rows_include_pa_verified():
    pa_id, _ = _make("U1")
    conn = get_conn()
    conn.execute("UPDATE etf_pa SET pa_verified_by_po_fin='2026-11-05' WHERE id=?", (pa_id,))
    conn.commit()
    conn.close()
    row = [r for r in get_pa_flat(COMPANY_ID, "agri", "active") if r["pa_id"] == pa_id][0]
    assert row["pa_verified_by_po_fin"] == "2026-11-05"


def test_update_and_bulk_accept_pa_verified_manually():
    pa_id, _ = _make("U2")
    assert approve_pa_fc(pa_id, COMPANY_ID, "agri")["ok"] is True
    assert update_pa(pa_id, COMPANY_ID, {"pa_verified_by_po_fin": "2026-11-05"}, "agri")["ok"] is True
    assert _verified(pa_id) == "2026-11-05"
    # edit lain tanpa kunci tersebut tidak boleh mengosongkannya
    update_pa(pa_id, COMPANY_ID, {"keterangan": "catatan"}, "agri")
    assert _verified(pa_id) == "2026-11-05"
    assert bulk_update_pa([pa_id], "pa_verified_by_po_fin", "2026-11-06", COMPANY_ID, "agri")["ok"] is True
    assert _verified(pa_id) == "2026-11-06"


def test_export_columns_include_pa_verified_after_recv():
    pa_id, _ = _make("U3")
    conn = get_conn()
    conn.execute("UPDATE etf_pa SET pa_verified_by_po_fin='2026-11-05' WHERE id=?", (pa_id,))
    conn.commit()
    conn.close()
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(export_pa_excel(COMPANY_ID, "agri")))
    ws = wb.active
    headers = [c.value for c in ws[1]]
    assert headers.index("PA Verified PO Fin") == headers.index("PA Recv PO Fin") + 1
    col = headers.index("PA Verified PO Fin") + 1
    assert "2026-11-05" in [ws.cell(row=r, column=col).value for r in range(2, ws.max_row + 1)]


def test_serah_log_route_returns_rows_for_prportal_pa_only(client):
    _login(client)
    pa_id, num = _ready("U4")
    _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER})
    r = client.get(f"/etf-payment-application/{pa_id}/serah-log?tab=agri")
    body = r.get_json()
    assert r.status_code == 200 and body["ok"] is True
    assert [x["kejadian"] for x in body["rows"]] == ["diserahkan"] and body["rows"][0]["oleh"] == OWNER
    # PA yang dibuat di Flow (bukan PR Portal): tanpa riwayat
    conn = get_conn()
    conn.execute("UPDATE etf_pa SET source='flow' WHERE id=?", (pa_id,))
    conn.commit()
    conn.close()
    assert client.get(f"/etf-payment-application/{pa_id}/serah-log?tab=agri").get_json()["rows"] == []
    assert client.get("/etf-payment-application/999999/serah-log?tab=agri").get_json()["rows"] == []


def test_template_has_new_column_log_link_and_colspan():
    from jinja2 import Environment, FileSystemLoader
    src = open(TEMPLATE, encoding="utf-8").read()
    Environment(loader=FileSystemLoader(os.path.dirname(TEMPLATE))).parse(src)
    assert "<th>PA Verified PO Fin</th>" in src and "r.pa_verified_by_po_fin" in src
    assert src.index("<th>PA Recv PO Fin</th>") < src.index("<th>PA Verified PO Fin</th>") < src.index("<th>Approval HTj</th>")
    assert 'colspan="35"' in src and "serah-log" in src
    assert '<option value="pa_verified_by_po_fin">' in src and 'id="edit-verified"' in src


def test_field_col_matches_rendered_td_index(client):
    """FIELD_COL (dipakai skrip untuk memperbarui sel di tempat) harus sejajar dengan urutan <td> pada baris yang dirender."""
    import re
    from html.parser import HTMLParser
    _login(client)
    pa_id, _ = _make("U5")
    vals = {"doc_received_by_educ": "2026-01-01", "received_pa_from_educ": "2026-01-02", "checked_by_fincon": "2026-01-03",
            "approved_by_htj_1": "2026-01-04", "send_pa_back_to_educ": "2026-01-05", "pa_received_by_po_fin": "2026-01-06",
            "pa_verified_by_po_fin": "2026-01-07", "approval_by_htj_2": "2026-01-08", "nomor_pam": "PAM-X-1", "tanggal_bayar": "2026-01-09"}
    conn = get_conn()
    sets = ", ".join(f"{k}=?" for k in vals)
    conn.execute(f"UPDATE etf_pa SET {sets}, status='open' WHERE id=?", (*vals.values(), pa_id))
    conn.commit()
    conn.close()
    html = client.get("/etf-payment-application/?tab=agri&sf=all&page_size=500").get_data(as_text=True)
    m = re.search(r'<tr data-pa-id="%d".*?</tr>' % pa_id, html, re.S)
    assert m, "baris PA tidak ditemukan di halaman"

    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.cells, self.cur = [], None
        def handle_starttag(self, tag, attrs):
            if tag == "td":
                self.cur = []
        def handle_endtag(self, tag):
            if tag == "td" and self.cur is not None:
                self.cells.append("".join(self.cur).strip())
                self.cur = None
        def handle_data(self, d):
            if self.cur is not None:
                self.cur.append(d)
    p = P()
    p.feed(m.group(0))
    col = {k: int(v) for k, v in re.findall(r"^\s*(\w+):\s+(\d+),", re.search(r"const FIELD_COL = \{(.*?)\};", html, re.S).group(1), re.M)}
    for field, v in vals.items():
        assert p.cells[col[field]] == v, f"{field}: FIELD_COL={col[field]} -> '{p.cells[col[field]]}' (harus {v})"
    assert p.cells[col["status"]].lower().startswith("open"), f"status: '{p.cells[col['status']]}'"


def test_inline_update_uses_field_col_for_status_cell_not_hardcoded_index():
    src = open(TEMPLATE, encoding="utf-8").read()
    block = src[src.index("function _updateRowCells"):]
    block = block[:block.index("\n}\n")]
    assert 'querySelectorAll("td")[29]' not in block, "indeks tetap rawan salah setelah kolom bertambah"
    assert 'querySelectorAll("td")[FIELD_COL.status]' in block
