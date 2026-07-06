from database import get_conn


def _login(client):
    client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})


def _select_smt_company(client):
    client.post("/select-company", data={"company_id": "1"})


def _coa_pam_row(sr):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, coa_expense FROM coa_pam WHERE klasifikasi_sr=?", (sr,)
    ).fetchone()
    conn.close()
    return dict(row)


def test_save_smt_lines_route_creates_pam(client):
    _login(client)
    _select_smt_company(client)
    coa = _coa_pam_row("Beasiswa")
    resp = client.post("/payment-memo/ipay/save-smt-lines", json={
        "tanggal": "2026-07-06", "pam_no": "PAM-200-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [{"coa_pam_id": coa["id"], "klasifikasi_sr": "Beasiswa",
                   "klasifikasi_mr": "Scholarship Expense", "gl_account": coa["coa_expense"],
                   "tipe_dokumen": "Invoice Payment – Non PO Invoice", "no_invoice": "INV-1",
                   "dpp": 100000, "ppn": 0, "cost_center": "POCCOM",
                   "budget_activity": "A", "keterangan": "Test"}],
    })
    data = resp.get_json()
    assert data["ok"] is True
    assert data["pam_no"] == "PAM-200-SMT-07-2026"


def test_pam_detail_route_includes_transaction_lines(client):
    _login(client)
    _select_smt_company(client)
    coa = _coa_pam_row("Beasiswa")
    client.post("/payment-memo/ipay/save-smt-lines", json={
        "tanggal": "2026-07-06", "pam_no": "PAM-201-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [{"coa_pam_id": coa["id"], "klasifikasi_sr": "Beasiswa",
                   "klasifikasi_mr": "Scholarship Expense", "gl_account": coa["coa_expense"],
                   "tipe_dokumen": "Downpayment to vendor", "no_invoice": "",
                   "dpp": 100000, "ppn": 0, "cost_center": "POCCOM",
                   "budget_activity": "A", "keterangan": "Test"}],
    })
    conn = get_conn()
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE pam_no='PAM-201-SMT-07-2026'"
    ).fetchone()["id"]
    conn.close()

    resp = client.get(f"/payment-memo/pam/{pam_id}/detail")
    data = resp.get_json()
    assert data["ok"] is True
    assert len(data["data"]["transaction_lines"]) == 1
    assert data["data"]["transaction_lines"][0]["tipe_dokumen"] == "Downpayment to vendor"


def test_index_route_still_renders_for_smt_company(client):
    # coa_pam_list is passed into the render_template context in this task,
    # but the template doesn't consume it as a JS global until Task 6 — so
    # this only asserts the route still renders successfully with the new
    # context kwarg added, not that the data appears in the HTML yet.
    _login(client)
    _select_smt_company(client)
    resp = client.get("/payment-memo/")
    assert resp.status_code == 200
