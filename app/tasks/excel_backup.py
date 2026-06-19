import os
import shutil
import datetime
import traceback
from modules.etf_payment_application.service import export_pa_excel

BACKUP_ROOT = r"Y:\Seagate\Harry\8. Backup\2. Financehub"

def cleanup_old_backups(keep_days=5):
    """
    Menghapus folder backup yang usianya lebih tua dari `keep_days` hari.
    Di dalam BACKUP_ROOT, folder dinamai dengan format YYYY-MM-DD.
    """
    if not os.path.exists(BACKUP_ROOT):
        return
    
    now = datetime.datetime.now()
    for item in os.listdir(BACKUP_ROOT):
        item_path = os.path.join(BACKUP_ROOT, item)
        if os.path.isdir(item_path):
            try:
                folder_date = datetime.datetime.strptime(item, "%Y-%m-%d")
                days_old = (now - folder_date).days
                if days_old > keep_days:
                    shutil.rmtree(item_path)
                    print(f"[Backup Scheduler] Cleaned up old backup folder: {item}")
            except ValueError:
                # Bukan folder berformat tanggal yang valid, abaikan.
                pass

def run_excel_backups():
    r"""
    Fungsi untuk mengenerate Excel backup dari modul PA AGRI, APP, LAND
    dan menyimpannya di Y:\Seagate\Harry\8. Backup\2. Financehub\YYYY-MM-DD\
    """
    try:
        # Asumsi ETF company_id adalah 2 sesuai data seed
        company_id = 2
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        target_dir = os.path.join(BACKUP_ROOT, today_str)
        os.makedirs(target_dir, exist_ok=True)
        print(f"[Backup Scheduler] Starting backup to {target_dir}")
        
        for tab in ["agri", "app", "land"]:
            try:
                excel_bytes = export_pa_excel(company_id=company_id, tab=tab)
                filename = f"PA_{tab.upper()}.xlsx"
                filepath = os.path.join(target_dir, filename)
                
                with open(filepath, "wb") as f:
                    f.write(excel_bytes)
                print(f"[Backup Scheduler] Successfully backed up {filename}")
            except Exception as e:
                print(f"[Backup Scheduler] Error exporting PA {tab}: {e}")
                traceback.print_exc()
                
        # Clean up
        cleanup_old_backups(keep_days=5)
        print("[Backup Scheduler] Backup and cleanup routine completed.")
    except Exception as e:
        print(f"[Backup Scheduler] Fatal error during backup: {e}")
        traceback.print_exc()
