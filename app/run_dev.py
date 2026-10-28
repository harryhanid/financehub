"""
run_dev.py — Server Development Lokal untuk Laptop Harry
--------------------------------------------------------
Menjalankan FLOW dalam mode DEVELOPMENT yang terisolasi penuh dari Komputer Tetap:
  - FH_ENV          = development
  - DB_SCHEMA       = financehub_staging (aman untuk eksperimen, tidak menyentuh data live)
  - ENABLE_MDNS     = 0 (tidak membajak domain http://financehub.local milik Komputer Tetap)
  - ENABLE_SCHEDULER= 0 (tidak menjalankan backup harian ke Y:\\Seagate\\Flow)
  - Port default    = 8082 (http://localhost:8082) dengan auto-reload aktif
"""
import os

# Paksa isolasi environment SEBELUM import config & app
os.environ.setdefault("FH_ENV", "development")
os.environ.setdefault("DB_SCHEMA", "financehub_staging")
os.environ["ENABLE_MDNS"] = "0"
os.environ["ENABLE_SCHEDULER"] = "0"

import config
from app import create_app

if __name__ == "__main__":
    port = int(os.environ.get("DEV_PORT", 8082))
    print("=" * 60)
    print("  FLOW — DEVELOPMENT SERVER (LAPTOP)")
    print("=" * 60)
    print(f"  URL Lokal     :  http://localhost:{port}")
    print(f"  FH_ENV        :  {config.FH_ENV}")
    print(f"  DB_SCHEMA     :  {config.DB_SCHEMA}  (STAGING - Aman dari data live)")
    print(f"  mDNS (.local) :  NONAKTIF (tidak bentrok dengan Komputer Tetap)")
    print(f"  Backup Cron   :  NONAKTIF (tidak menimpa backup Y:\\)")
    print(f"  SOP Storage   :  {config.SOP_STORAGE_DIR}")
    print("=" * 60)
    print()

    app = create_app()
    app.run(host="127.0.0.1", port=port, debug=True)
