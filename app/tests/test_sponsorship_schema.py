from database import get_conn


def _table_columns(conn, table_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {r["name"] for r in rows}


def test_sponsorship_perusahaan_table_exists(app):
    conn = get_conn()
    cols = _table_columns(conn, "sponsorship_perusahaan")
    conn.close()
    assert cols == {"cat1", "cat2", "cat3"}


def test_sponsorship_transaksi_table_exists(app):
    conn = get_conn()
    cols = _table_columns(conn, "sponsorship_transaksi")
    conn.close()
    expected = {
        "id", "company_id", "cat", "description", "tanggal_form_sponsor",
        "tanggal_payment", "cat1", "cat2", "cat3", "lembaga_perorangan",
        "perihal", "amount_request", "reff", "status", "cat4",
        "coa", "cc_total", "cc", "source", "created_at", "updated_at",
    }
    assert cols == expected


def test_sponsorship_transaksi_defaults(app):
    conn = get_conn()
    conn.execute(
        "INSERT INTO sponsorship_transaksi "
        "(company_id, cat, description, tanggal_form_sponsor, cat1, cat2, cat3, lembaga_perorangan, amount_request) "
        "VALUES (1, 'Sponsorship', 'Sosial', '2026-01-01', 'SMART', 'AGRI', 'AGRI', 'Test Lembaga', 1000)"
    )
    conn.commit()
    row = conn.execute("SELECT * FROM sponsorship_transaksi WHERE lembaga_perorangan = 'Test Lembaga'").fetchone()
    conn.close()
    assert row["coa"] == "701078002"
    assert row["cc_total"] == "SMT - Corporate Communication"
    assert row["cc"] == "POSPON"
    assert row["source"] == "Sponsor"


def test_config_sponsorship_constants():
    import config
    assert config.SPONSORSHIP_CAT == ["Sponsorship", "CSR Gedung"]
    assert len(config.SPONSORSHIP_DESCRIPTION) == 10
    assert "Akademisi" in config.SPONSORSHIP_DESCRIPTION
    assert config.SPONSORSHIP_CAT4 == ["Include", "Exclude"]
    assert config.SPONSORSHIP_PILLARS == ["APP", "AGRI", "ENERGY & FINANCE", "PROPERTY"]
