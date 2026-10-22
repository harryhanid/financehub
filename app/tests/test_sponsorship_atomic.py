"""Task 13 (atomic-flows.md): alur multi-tulisan sponsorship harus all-or-nothing di Postgres.

Langkah terakhir dipaksa gagal lewat CHECK ... NOT VALID sementara, lalu dicek bahwa semua
tabel yang disentuh tidak berubah.
"""
import io
import datetime

import openpyxl
import pytest

from database import get_conn
from fhdb.errors import OperationalError
import modules.sponsorship.service as svc
from modules.sponsorship.service import (
    seed_perusahaan, create_transaksi, create_transaksi_bulk, sync_transaksi_excel,
    delete_transaksi, list_perusahaan,
)

SMT = 1


def _snapshot():
    conn = get_conn()
    p = [dict(r) for r in conn.execute("SELECT * FROM sponsorship_perusahaan ORDER BY cat1").fetchall()]
    t = [dict(r) for r in conn.execute("SELECT * FROM sponsorship_transaksi ORDER BY id").fetchall()]
    conn.close()
    return p, t


def _add_check(table, name, expr):
    conn = get_conn()
    conn.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr}) NOT VALID")
    conn.close()


def _drop_check(table, name):
    conn = get_conn()
    conn.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
    conn.close()


def _bulk_payload(lines):
    return {
        "cat": "Sponsorship", "description": "Sosial", "tanggal_form_sponsor": "2026-03-01",
        "lembaga_perorangan": "Yayasan X", "perihal": "Acara", "lines": lines,
    }


# --- seed_perusahaan ---------------------------------------------------------

def test_seed_perusahaan_atomic_on_failure(app):
    seed_perusahaan([("SMART", "AGRI", "AGRI")])
    before = _snapshot()
    with pytest.raises(Exception):
        # baris terakhir melanggar NOT NULL (cat2)
        seed_perusahaan([("IKPP", "APP", "APP"), ("NEW1", "AGRI", "AGRI"), ("BAD", None, "APP")])
    assert _snapshot() == before


def test_seed_perusahaan_counts_only_new_rows(app):
    seed_perusahaan([("SMART", "AGRI", "AGRI")])
    assert seed_perusahaan([("SMART", "AGRI", "AGRI"), ("IKPP", "APP", "APP")]) == 1
    assert seed_perusahaan([]) == 0


# --- create_transaksi_bulk ---------------------------------------------------

def test_create_transaksi_bulk_atomic_on_failure(app):
    seed_perusahaan([("SMART", "AGRI", "AGRI"), ("IKPP", "APP", "APP")])
    before = _snapshot()
    _add_check("sponsorship_transaksi", "t13_no_fail", "amount_request <> 999")
    try:
        result = create_transaksi_bulk(SMT, _bulk_payload([
            {"cat1": "SMART", "amount_request": 100},
            {"cat1": "IKPP", "amount_request": 200},
            {"cat1": "SMART", "amount_request": 999},  # INSERT terakhir gagal
        ]))
    finally:
        _drop_check("sponsorship_transaksi", "t13_no_fail")
    assert result["ok"] is False
    assert _snapshot() == before


def test_create_transaksi_bulk_validation_failure_saves_nothing(app):
    """Dulu rollback() di tengah loop: baris sebelum baris invalid juga batal."""
    seed_perusahaan([("SMART", "AGRI", "AGRI")])
    before = _snapshot()
    r1 = create_transaksi_bulk(SMT, _bulk_payload([
        {"cat1": "SMART", "amount_request": 100},
        {"cat1": "NOT-THERE", "amount_request": 200},
    ]))
    assert r1 == {"ok": False, "pesan": "Baris 2: Cat1 'NOT-THERE' tidak ditemukan."}
    r2 = create_transaksi_bulk(SMT, _bulk_payload([
        {"cat1": "SMART", "amount_request": 100},
        {"cat1": "SMART", "amount_request": "abc"},
    ]))
    assert r2 == {"ok": False, "pesan": "Baris 2: Amount Request harus berupa angka."}
    assert _snapshot() == before


def test_create_transaksi_bulk_success_saves_all_lines(app):
    seed_perusahaan([("SMART", "AGRI", "AGRI"), ("IKPP", "APP", "APP")])
    result = create_transaksi_bulk(SMT, _bulk_payload([
        {"cat1": "SMART", "amount_request": 100, "cat4": "Include"},
        {"cat1": "IKPP", "amount_request": "200.5"},
    ]))
    assert result == {"ok": True, "pesan": "Berhasil menyimpan 2 transaksi Sponsorship."}
    _, rows = _snapshot()
    assert [(r["cat1"], r["cat3"], r["amount_request"], r["cat4"], r["coa"], r["source"]) for r in rows] == [
        ("SMART", "AGRI", 100.0, "Include", "701078002", "Sponsor"),
        ("IKPP", "APP", 200.5, None, "701078002", "Sponsor"),
    ]


def test_create_transaksi_bulk_reraises_operational_error(app, monkeypatch):
    seed_perusahaan([("SMART", "AGRI", "AGRI")])

    def boom(_cat1):
        raise OperationalError("db down", sqlstate="08006")
    monkeypatch.setattr(svc, "get_perusahaan", boom)
    with pytest.raises(OperationalError):
        create_transaksi_bulk(SMT, _bulk_payload([{"cat1": "SMART", "amount_request": 1}]))


# --- sync_transaksi_excel ----------------------------------------------------

def _sync_xlsx(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID", "Cat", "Desc", "Tgl Form", "Tgl Pay", "Cat1", "Cat2", "Cat3", "Lembaga", "Perihal",
               "Amount", "APP", "ENERGY", "PROPERTY", "AGRI", "Reff", "Status", "Cat4", "COA",
               "CC Total", "CC", "Source"])
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _row(tx_id, cat1, cat2, cat3, lembaga, amount, coa=None):
    return [tx_id, "Sponsorship", "Sosial", datetime.datetime(2026, 2, 3), None, cat1, cat2, cat3,
            lembaga, "Perihal", amount, 0, 0, 0, 0, None, None, None, coa, None, None, None]


def _existing_tx():
    seed_perusahaan([("SMART", "AGRI", "AGRI")])
    r = create_transaksi(SMT, {
        "cat": "Sponsorship", "description": "Sosial", "tanggal_form_sponsor": "2026-01-10",
        "cat1": "SMART", "lembaga_perorangan": "Lama", "amount_request": 50,
    })
    return r["id"]


def test_sync_transaksi_excel_atomic_on_failure(app):
    tx_id = _existing_tx()
    before = _snapshot()
    data = _sync_xlsx([
        _row(None, "NEWCO", "APP", "APP", "Baru", 10),        # vendor baru + INSERT
        _row(tx_id, "SMART", "MINING", "AGRI", "Diubah", 20),  # UPDATE vendor + UPDATE transaksi
        _row(None, "SMART", "MINING", "AGRI", "FAIL-ME", 30),  # INSERT terakhir gagal
    ])
    _add_check("sponsorship_transaksi", "t13_no_fail_sync", "lembaga_perorangan <> 'FAIL-ME'")
    try:
        result = sync_transaksi_excel(SMT, data)
    finally:
        _drop_check("sponsorship_transaksi", "t13_no_fail_sync")
    assert result["ok"] is False
    assert _snapshot() == before


def test_sync_transaksi_excel_validation_failure_saves_nothing(app):
    tx_id = _existing_tx()
    before = _snapshot()
    data = _sync_xlsx([
        _row(None, "NEWCO", "APP", "APP", "Baru", 10),
        _row(tx_id, "SMART", "AGRI", "AGRI", "Diubah", 20),
        _row(None, "OTHER", "", "", "X", 5),  # vendor baru tanpa cat2/cat3
    ])
    result = sync_transaksi_excel(SMT, data)
    assert result == {"ok": False, "pesan": "Baris 4: Cat1 'OTHER' baru, namun Cat2 atau Cat3 kosong di Excel."}
    assert _snapshot() == before


def test_sync_transaksi_excel_success_applies_all_rows(app):
    tx_id = _existing_tx()
    data = _sync_xlsx([
        _row(None, "NEWCO", "APP", "APP", "Baru", 10, coa=701078002),
        _row(None, "NEWCO", "APP", "PROPERTY", "Baru 2", 11),  # cat1 baru yang sama: dedupe
        _row(tx_id, "SMART", "MINING", "AGRI", "Diubah", 20),
        [None] * 22,  # baris kosong dilewati
    ])
    result = sync_transaksi_excel(SMT, data)
    assert result == {"ok": True, "pesan": "Sync sukses: 1 di-update, 2 ditambah."}
    vendors = {r["cat1"]: (r["cat2"], r["cat3"]) for r in list_perusahaan()}
    assert vendors == {"SMART": ("MINING", "AGRI"), "NEWCO": ("APP", "PROPERTY")}
    _, rows = _snapshot()
    by_lembaga = {r["lembaga_perorangan"]: r for r in rows}
    assert set(by_lembaga) == {"Diubah", "Baru", "Baru 2"}
    assert by_lembaga["Diubah"]["id"] == tx_id
    assert by_lembaga["Diubah"]["amount_request"] == 20.0
    assert by_lembaga["Diubah"]["tanggal_form_sponsor"] == "2026-02-03"
    assert by_lembaga["Baru"]["coa"] == "701078002"
    assert by_lembaga["Baru 2"]["cc"] == "POSPON"


def test_sync_transaksi_excel_reraises_operational_error(app, monkeypatch):
    _existing_tx()

    def boom(_cat1):
        raise OperationalError("db down", sqlstate="08006")
    monkeypatch.setattr(svc, "get_perusahaan", boom)
    with pytest.raises(OperationalError):
        sync_transaksi_excel(SMT, _sync_xlsx([_row(None, "SMART", "AGRI", "AGRI", "X", 1)]))


def test_delete_transaksi_reraises_operational_error(app, monkeypatch):
    tx_id = _existing_tx()
    real_get_conn = svc.get_conn

    class _Conn:
        def __init__(self):
            self._c = real_get_conn()

        def execute(self, sql, params=()):
            if sql.lstrip().upper().startswith("DELETE"):
                raise OperationalError("db down", sqlstate="08006")
            return self._c.execute(sql, params)

        def __getattr__(self, name):
            return getattr(self._c, name)

    monkeypatch.setattr(svc, "get_conn", _Conn)
    with pytest.raises(OperationalError):
        delete_transaksi(tx_id, SMT)


# --- filter / tahun ----------------------------------------------------------

def test_keyword_filter_is_case_insensitive_and_tahun_accepts_int(app):
    _existing_tx()
    assert len(svc.list_transaksi(SMT, {"keyword": "lAMa"})) == 1
    assert len(svc.list_transaksi(SMT, {"tahun": [2026]})) == 1
    assert len(svc.list_transaksi(SMT, {"tahun": 2026, "bulan": ["1"]})) == 1
    assert svc.get_available_years(SMT) == ["2026"]
