import os
import sys

# Tambahkan folder 'app' ke system path agar bisa import modul Flask
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app_dir = os.path.join(base_dir, 'app')
sys.path.insert(0, app_dir)

from app import create_app
from tasks.flow_backup import run_flow_backups

if __name__ == "__main__":
    print("Mempersiapkan manual backup FLOW...")
    app = create_app()
    with app.app_context():
        run_flow_backups()
    print("Selesai! Silakan cek Y:\\Seagate\\Flow.")
