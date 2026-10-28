import pytest
import io
import openpyxl
from modules.sponsorship.service import get_transaksi, list_transaksi
from database import get_conn

def sync_transaksi_excel(company_id: int, file_bytes: bytes) -> dict:
    pass

def test_sync_transaksi_excel(app_context, seed_sponsorship_data):
    # Get existing data
    rows = list_transaksi(1, {})
    initial_count = len(rows)
    assert initial_count > 0
    
    first_id = rows[0]['id']
    old_amount = rows[0]['amount_request']
    
    # Create an excel file in memory
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "ID", "Cat", "Description", "Tanggal Form", "Tanggal Payment",
        "Cat1", "Cat2", "Cat3", "Lembaga / Perorangan", "Perihal",
        "Amount Request", "APP", "ENERGY", "PROPERTY", "AGRI",
        "Reff", "Status", "Cat4", "COA", "CC Total", "CC", "Source"
    ])
    
    # 1. Update an existing row
    ws.append([
        first_id, "Sponsorship", "Test Desc", "2026-09-01", "",
        "SMART", "AGRI", "AGRI", "Test Lembaga", "Update Perihal",
        old_amount + 5000, 0, 0, 0, 0,
        "", "", "Include", "70", "CC", "POS", "Sponsor"
    ])
    
    # 2. Insert a new row (ID is empty)
    ws.append([
        None, "Sponsorship", "Test Desc 2", "2026-09-02", "",
        "BSML", "ENERGY", "ENERGY", "New Lembaga", "New Perihal",
        15000, 0, 0, 0, 0,
        "", "", "Include", "70", "CC", "POS", "Sponsor"
    ])
    
    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_bytes = file_stream.getvalue()
    
    from modules.sponsorship.service import sync_transaksi_excel
    # Run sync
    res = sync_transaksi_excel(1, file_bytes)
    assert res['ok'] == True
    
    # Verify update
    updated_row = get_transaksi(first_id)
    assert updated_row['perihal'] == "Update Perihal"
    assert updated_row['amount_request'] == old_amount + 5000
    
    # Verify insert
    new_rows = list_transaksi(1, {})
    assert len(new_rows) == initial_count + 1
    
    # Verify the new one exists
    found = any(r['lembaga_perorangan'] == "New Lembaga" for r in new_rows)
    assert found == True

