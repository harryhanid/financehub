import sys
import os

# Add C:\Financehub\app to path
app_dir = r"C:\Financehub\app"
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from app import create_app
from database import init_db
from modules.sponsorship.exports import export_data_excel

app = create_app()
with app.app_context():
    init_db()
    
    # filters = {"tahun": ["2026"]}
    # If the app stores year as string in 'tanggal_form_sponsor', filtering happens in list_transaksi
    xls_bytes = export_data_excel(1, {"tahun": ["2026"]})
    
    with open('C:\\Financehub\\Sponsorship - MASTER.xlsx', 'wb') as f:
        f.write(xls_bytes)
    
    print("File generated successfully.")
