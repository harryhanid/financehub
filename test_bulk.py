import sys
sys.path.append('C:\\Financehub\\app')
from modules.sponsorship.service import create_transaksi_bulk
payload = {
    "cat": "Sponsorship", "description": "Organisasi Profesional", "lembaga_perorangan": "Test",
    "tanggal_form_sponsor": "2026-09-01", "perihal": "Test", "lines": [
        {"cat1": "SMART", "cat4": "Exclude", "amount_request": 100000}
    ]
}
try:
    res = create_transaksi_bulk(1, payload)
    print("Result:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
