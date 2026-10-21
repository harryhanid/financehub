import pytest
from database import get_conn
from modules.beasiswa.service import (
    get_dashboard_pillar_yearly,
    get_dashboard_trend_transactions,
)

COMPANY_ID = 2

@pytest.fixture(autouse=True)
def setup_pillar_test_data():
    conn = get_conn()
    try:
        conn.execute("DELETE FROM payment_beasiswa WHERE company_id = ? AND siswa_code = 'S991'", (COMPANY_ID,))
        conn.execute("DELETE FROM siswa WHERE company_id = ? AND code = 'S991'", (COMPANY_ID,))

        # Seed siswa
        conn.execute(
            "INSERT INTO siswa (company_id, code, nama, program, jenjang, angkatan, status) VALUES (?, 'S991', 'Test Siswa', 'Reguler', 'S1', '2023', 'Aktif')",
            (COMPANY_ID,)
        )

        # Seed payments with various pillars
        sample_payments = [
            (COMPANY_ID, "S991", "2023-01-15", "AGRI", "By Pendidikan", 1000000, "complete"),
            (COMPANY_ID, "S991", "2023-02-15", "APP", "By Pendidikan", 2000000, "complete"),
            (COMPANY_ID, "S991", "2023-03-15", "FINANCE", "By Pendidikan", 3000000, "complete"),
            (COMPANY_ID, "S991", "2023-04-15", "LAND", "By Pendidikan", 4000000, "complete"),
            (COMPANY_ID, "S991", "2026-05-15", "PROPERTY", "By Pendidikan", 5000000, "complete"),
            (COMPANY_ID, "S991", "2026-06-15", "LAND", "By Pendidikan", 6000000, "complete"),
            (COMPANY_ID, "S991", "2026-07-15", "EFIN", "By Pendidikan", 7000000, "complete"),
            (COMPANY_ID, "S991", "2026-08-15", "SETF", "By Pendidikan", 8000000, "complete"),
        ]

        for p in sample_payments:
            conn.execute(
                """
                INSERT INTO payment_beasiswa (company_id, siswa_code, tanggal, pillar, cat1, amount, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                p,
            )
        conn.commit()
    finally:
        conn.close()

    yield

    conn = get_conn()
    try:
        conn.execute("DELETE FROM payment_beasiswa WHERE company_id = ? AND siswa_code = 'S991'", (COMPANY_ID,))
        conn.execute("DELETE FROM siswa WHERE company_id = ? AND code = 'S991'", (COMPANY_ID,))
        conn.commit()
    finally:
        conn.close()


def test_pillar_yearly_merges_land_into_property_and_finance_into_efin():
    data = get_dashboard_pillar_yearly(COMPANY_ID, programs=["Reguler"])
    assert len(data) == 2  # 2023 and 2026

    row_2023 = next((r for r in data if r["tahun"] == 2023), None)
    assert row_2023 is not None
    # 2023: AGRI 1M, APP 2M, FINANCE 3M -> EFIN 3M, LAND 4M -> PROPERTY 4M
    assert "LAND" not in row_2023["pillars"]
    assert "FINANCE" not in row_2023["pillars"]
    assert row_2023["pillars"].get("EFIN") == 3000000
    assert row_2023["pillars"].get("PROPERTY") == 4000000
    assert row_2023["pillars"].get("AGRI") == 1000000
    assert row_2023["pillars"].get("APP") == 2000000

    row_2026 = next((r for r in data if r["tahun"] == 2026), None)
    assert row_2026 is not None
    # 2026: PROPERTY 5M + LAND 6M -> PROPERTY 11M, EFIN 7M, SETF 8M
    assert "LAND" not in row_2026["pillars"]
    assert row_2026["pillars"].get("PROPERTY") == 11000000
    assert row_2026["pillars"].get("EFIN") == 7000000
    assert row_2026["pillars"].get("SETF") == 8000000


def test_filter_expansion_for_property_and_efin():
    # When filtering by PROPERTY, it must include PROPERTY and LAND (4M in 2023 + 11M in 2026 = 15M)
    prop_data = get_dashboard_pillar_yearly(COMPANY_ID, programs=["Reguler"], pillars=["PROPERTY"])
    tot_prop = sum(sum(r["pillars"].values()) for r in prop_data)
    assert tot_prop == 15000000

    # When filtering by EFIN, it must include FINANCE and EFIN (3M in 2023 + 7M in 2026 = 10M)
    efin_data = get_dashboard_pillar_yearly(COMPANY_ID, programs=["Reguler"], pillars=["EFIN"])
    tot_efin = sum(sum(r["pillars"].values()) for r in efin_data)
    assert tot_efin == 10000000


def test_trend_transactions_mapping():
    # Transactions filtered by PROPERTY should include LAND, and pillar mapped to PROPERTY
    prop_trx = get_dashboard_trend_transactions(COMPANY_ID, programs=["Reguler"], pillars=["PROPERTY"])
    assert len(prop_trx) == 3  # 1 LAND in 2023, 1 PROPERTY in 2026, 1 LAND in 2026
    for t in prop_trx:
        assert t["pillar"] == "PROPERTY"
    assert sum(float(t["amount"]) for t in prop_trx) == 15000000

    # Transactions filtered by EFIN should include FINANCE, and pillar mapped to EFIN
    efin_trx = get_dashboard_trend_transactions(COMPANY_ID, programs=["Reguler"], pillars=["EFIN"])
    assert len(efin_trx) == 2  # 1 FINANCE in 2023, 1 EFIN in 2026
    for t in efin_trx:
        assert t["pillar"] == "EFIN"
    assert sum(float(t["amount"]) for t in efin_trx) == 10000000
