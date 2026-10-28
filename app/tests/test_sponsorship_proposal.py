import pytest
from modules.sponsorship.service import (
    list_proposals, count_proposals, get_proposal,
    create_proposal, update_proposal, update_proposal_status, delete_proposal
)
from modules.sponsorship.exports import export_proposal_form_excel, terbilang_id


def test_terbilang_id():
    assert terbilang_id(0) == "Nol"
    assert terbilang_id(1) == "Satu"
    assert terbilang_id(12) == "Dua Belas"
    assert terbilang_id(100) == "Seratus"
    assert terbilang_id(150000000) == "Seratus Lima Puluh Juta"
    assert terbilang_id(300000000) == "Tiga Ratus Juta"
    assert terbilang_id(10000000000) == "Sepuluh Miliar"


def test_proposal_lifecycle():
    # 1. Create
    res = create_proposal(1, {
        "tanggal": "2026-10-28",
        "diajukan_oleh": "AR/JT",
        "referensi": "Pytest Referensi",
        "kegiatan": "Pytest Kegiatan",
        "app_amount": 50000000,
        "agri_amount": 50000000,
        "total_amount": 100000000,
        "status": "Open"
    })
    assert res["ok"] is True
    prop_id = res["id"]
    prop_no = res["nomor_proposal"]
    assert prop_no.startswith("PROP-2026-")

    # 2. Get
    p = get_proposal(1, prop_id)
    assert p is not None
    assert p["referensi"] == "Pytest Referensi"
    assert p["total_amount"] == 100000000
    assert p["status"] == "Open"

    # 3. Status update
    st_res = update_proposal_status(1, prop_id, "Approved", "2026-10-28")
    assert st_res["ok"] is True
    p2 = get_proposal(1, prop_id)
    assert p2["status"] == "Approved"
    assert p2["approval_date"] == "2026-10-28"

    # 4. Export Excel test
    xls_bytes = export_proposal_form_excel(p2)
    assert isinstance(xls_bytes, bytes)
    assert len(xls_bytes) > 2000

    # 5. Delete
    del_res = delete_proposal(1, prop_id)
    assert del_res["ok"] is True
    assert get_proposal(1, prop_id) is None
