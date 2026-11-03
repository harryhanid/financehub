import os; os.environ['GDRIVE_INTERACTIVE_AUTH'] = '1'  # otorisasi manual di komputer dev (di server alur ini dimatikan)
from utils.gdrive_service import get_gdrive_service; print("Membuka browser untuk otentikasi..."); get_gdrive_service(); print("Berhasil! token.json telah dibuat.")
