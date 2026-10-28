import sys
sys.path.append('C:\\Financehub\\app')
from app import create_app
from database import init_db
from modules.sponsorship.exports import export_data_excel

# Setup flask app context
app = create_app()
with app.app_context():
    init_db()
    
    xls_bytes = export_data_excel(1, {"tahun": ["2026"]})
    
    with open('C:\\Financehub\\Sponsorship - MASTER.xlsx', 'wb') as f:
        f.write(xls_bytes)
    
    print("File generated successfully.")
