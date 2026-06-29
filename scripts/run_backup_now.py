import os
import sys

# Tambahkan folder 'app' ke system path agar bisa import modul Flask
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app_dir = os.path.join(base_dir, 'app')
sys.path.insert(0, app_dir)

from app import create_app
from tasks.excel_backup import run_excel_backups

if __name__ == "__main__":
    print("Mempersiapkan manual backup...")
    app = create_app()
    with app.app_context():
        run_excel_backups()
    print("Selesai! Silakan cek folder backup Anda.")
