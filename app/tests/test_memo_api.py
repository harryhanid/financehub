import pytest
from app import create_app


def _login(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
    return r.get_json().get("access_token", "")


def test_get_draft_payments_empty(client):
    token = _login(client)
    r = client.get("/api/v1/payment-draft?company=ETF",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
    assert r.get_json()["data"] == []


def test_list_memo_empty(client):
    token = _login(client)
    r = client.get("/api/v1/payment-memo?company=ETF",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert isinstance(r.get_json()["data"], list)


def test_create_memo_no_items_returns_400(client):
    # Role system removed — any authenticated user can attempt to create memo;
    # empty item_ids returns 400 (business validation), not 403.
    token = _login(client)
    r = client.post("/api/v1/payment-memo",
                    json={"company": "ETF", "tanggal": "2026-05-30", "notes": "", "item_ids": []},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_payment_draft_invalid_company(client):
    token = _login(client)
    r = client.get("/api/v1/payment-draft?company=INVALID",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_list_memo_invalid_company(client):
    token = _login(client)
    r = client.get("/api/v1/payment-memo?company=XYZ",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_payment_draft_requires_auth(client):
    r = client.get("/api/v1/payment-draft?company=ETF")
    assert r.status_code == 401


# ── PAM API tests ────────────────────────────────────────────────────────────

def test_get_coa_list(client):
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get("/payment-memo/coa",
                    headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert len(data["coa"]) == 14


def test_get_pam_list_empty(client):
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get("/payment-memo/pam",
                    headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert data["rows"] == []


def test_update_pam_gl_account_via_api(client):
    from modules.payment_memo.service import create_pam_record
    from database import get_conn
    # Seed a PAM record directly
    conn = get_conn()
    try:
        pam_no = create_pam_record(conn, 2, "ETF", {
            "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
            "keterangan": "Harry", "total_amount": 1000000.0, "payment_ids": [],
        })
        conn.commit()
        pam_id = conn.execute(
            "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
        ).fetchone()["id"]
    finally:
        conn.close()

    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.post(f"/payment-memo/pam/{pam_id}/gl-account",
                     json={"gl_account": "70107800"},
                     headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    assert rv.get_json()["ok"] is True


def test_pam_detail_includes_payments(client):
    from modules.payment_memo.service import create_pam_record
    from database import get_conn
    conn = get_conn()
    try:
        pam_no = create_pam_record(conn, 2, "ETF", {
            "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
            "keterangan": "Test", "total_amount": 5000000.0, "payment_ids": [],
        })
        conn.execute(
            "INSERT INTO siswa (company_id,code,nama,bank,norek,namarek,jenjang,program,status)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (2, "S001", "Budi", "BCA", "123456", "Budi", "S1", "SMART", "Aktif"),
        )
        conn.execute(
            "INSERT INTO payment_beasiswa"
            " (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,pam,status)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (2, "S001", "General", "Sem 1", "2026-05-31", 5000000, "ETF", "PT. SMART Tbk", pam_no, "open"),
        )
        conn.commit()
        pam_id = conn.execute(
            "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
        ).fetchone()["id"]
    finally:
        conn.close()

    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get(f"/payment-memo/pam/{pam_id}/detail",
                    headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["ok"] is True
    assert "payments" in body["data"]
    assert len(body["data"]["payments"]) == 1
    assert body["data"]["payments"][0]["siswa_code"] == "S001"
    assert body["data"]["payments"][0]["amount"] == 5000000


_CUSTOM_PAYLOAD = {
    "pam_no": "PAM-001-ETF-05-2026",
    "pam_date": "2026-05-26",
    "requestors_name": "Jany Turkanda",
    "department": "HR",
    "cost_center": "1008C1POFF",
    "gl_account": "70110230",
    "so_sc": "",
    "pt": "PT. SMART Tbk",
    "bu_upstream": False, "bu_downstream": False, "bu_corporate": True,
    "type_downpayment": False, "type_invoice": True, "type_advance": False,
    "vendor_name": "Terlampir",
    "invoice_memo_no": "-",
    "total_amount": 5000000,
    "due_date": "2026-06-26",
    "bank_account_name": "Terlampir",
    "bank_name": "Terlampir",
    "bank_account_no": "Terlampir",
    "approved_by_1": "Hong Tjhin",
    "approved_by_2": "Tenti Kidjo",
}


def _seed_pam_for_custom(conn):
    from modules.payment_memo.service import create_pam_record
    pam_no = create_pam_record(conn, 2, "ETF", {
        "pam_date": "2026-05-26", "pt": "PT. SMART Tbk",
        "keterangan": "Test", "total_amount": 5000000.0, "payment_ids": [],
    })
    conn.commit()
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
    ).fetchone()["id"]
    return pam_id, pam_no


def test_export_pam_pdf_custom_route_returns_pdf(client):
    from database import get_conn
    conn = get_conn()
    try:
        pam_id, pam_no = _seed_pam_for_custom(conn)
    finally:
        conn.close()

    payload = {**_CUSTOM_PAYLOAD, "pam_no": pam_no}
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.post(f"/payment-memo/pam/{pam_id}/export/pdf-custom",
                     json=payload,
                     headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    assert rv.content_type == "application/pdf"
    assert rv.data[:4] == b'%PDF'


def test_export_pam_excel_custom_route_returns_xlsx(client):
    import zipfile, io as _io
    from database import get_conn
    conn = get_conn()
    try:
        pam_id, pam_no = _seed_pam_for_custom(conn)
    finally:
        conn.close()

    payload = {**_CUSTOM_PAYLOAD, "pam_no": pam_no}
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.post(f"/payment-memo/pam/{pam_id}/export/excel-custom",
                     json=payload,
                     headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    assert "spreadsheetml" in rv.content_type
    assert zipfile.is_zipfile(_io.BytesIO(rv.data))


# ── Days of PAM route ─────────────────────────────────────────────────────────

def _seed_pam_payment(client):
    """Seed satu payment_beasiswa ber-PAM ke company ETF (id=2)."""
    from database import get_conn
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (2, "S001", "Budi")
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, tanggal, amount, pam)
           VALUES (?,?,?,?,?,?)""",
        (2, "S001", "Beasiswa", "2026-05-01", 5000000.0, "PAM-001-ETF-05-2026")
    )
    conn.commit()
    row_id = conn.execute(
        "SELECT id FROM payment_beasiswa WHERE siswa_code='S001'"
    ).fetchone()["id"]
    conn.close()
    return row_id


def test_days_of_pam_bulk_update_ok(client):
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"]   = 2
        sess["company_code"] = "ETF"
    row_id = _seed_pam_payment(client)
    r = client.post(
        "/payment-memo/days-of-pam/bulk-update",
        json={"ids": [row_id], "dates": {"tgl_receive": "2026-05-10"}},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["updated"] == 1


def test_days_of_pam_bulk_update_no_session(client):
    token = _login(client)
    # no company_id in session
    r = client.post(
        "/payment-memo/days-of-pam/bulk-update",
        json={"ids": [1], "dates": {"tgl_receive": "2026-05-10"}},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 400


def test_days_of_pam_bulk_update_invalid_ids(client):
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    r = client.post(
        "/payment-memo/days-of-pam/bulk-update",
        json={"ids": ["not-an-int"], "dates": {"tgl_receive": "2026-05-10"}},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 400


# ── Days of PAM candidates + search ──────────────────────────────────────────

def _seed_dop_row(company_id=2, pam_no="PAM-001-ETF-05-2026",
                  siswa_code="S099", nama="Harry", source="etf_agri"):
    """Seed one payment_beasiswa row + pam_records row that has a pam value."""
    from database import get_conn
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO siswa (company_id, code, nama) VALUES (?,?,?)",
            (company_id, siswa_code, nama)
        )
        conn.execute(
            """INSERT INTO payment_beasiswa
               (company_id, siswa_code, cat1, tanggal, amount, pam)
               VALUES (?,?,?,?,?,?)""",
            (company_id, siswa_code, "General", "2026-05-01", 3000000.0, pam_no)
        )
        conn.execute(
            "INSERT OR IGNORE INTO pam_records (company_id, pam_no, source) VALUES (?,?,?)",
            (company_id, pam_no, source)
        )
        conn.commit()
        row_id = conn.execute(
            "SELECT id FROM payment_beasiswa WHERE siswa_code=? AND company_id=?",
            (siswa_code, company_id)
        ).fetchone()["id"]
    finally:
        conn.close()
    return row_id


def test_get_dop_candidates_empty(client):
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get("/payment-memo/days-of-pam/candidates",
                    headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert data["candidates"] == []


def test_get_dop_candidates_with_data(client):
    _seed_dop_row()
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get("/payment-memo/days-of-pam/candidates",
                    headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert len(data["candidates"]) == 1
    c = data["candidates"][0]
    assert c["pam_no"] == "PAM-001-ETF-05-2026"
    assert c["siswa_code"] == "S099"
    assert c["nama"] == "Harry"


def test_dop_search_by_pam(client):
    _seed_dop_row()
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get(
        "/payment-memo/days-of-pam/search?pam=PAM-001-ETF-05-2026",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert len(data["rows"]) == 1
    assert data["rows"][0]["siswa_code"] == "S099"
    assert data["rows"][0]["pam_no"] == "PAM-001-ETF-05-2026"


def test_dop_search_by_nama(client):
    _seed_dop_row()
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get(
        "/payment-memo/days-of-pam/search?nama=harry",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert len(data["rows"]) == 1
    assert data["rows"][0]["siswa_code"] == "S099"
    assert data["rows"][0]["pam_no"] == "PAM-001-ETF-05-2026"


def test_dop_search_no_match(client):
    _seed_dop_row()
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get(
        "/payment-memo/days-of-pam/search?pam=NOPE-999",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert data["rows"] == []


def test_dop_candidates_requires_auth(client):
    # jwt_html_required redirects unauthenticated browser requests to login (302)
    rv = client.get("/payment-memo/days-of-pam/candidates")
    assert rv.status_code == 302


def test_dop_search_requires_auth(client):
    # jwt_html_required redirects unauthenticated browser requests to login (302)
    rv = client.get("/payment-memo/days-of-pam/search?pam=PAM-001-ETF-05-2026")
    assert rv.status_code == 302


def test_dop_candidates_no_session(client):
    token = _login(client)
    # no company_id in session
    rv = client.get("/payment-memo/days-of-pam/candidates",
                    headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 400


def test_dop_search_no_session(client):
    token = _login(client)
    rv = client.get("/payment-memo/days-of-pam/search?pam=PAM-001-ETF-05-2026",
                    headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 400
