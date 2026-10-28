with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    content = f.read()

import re

# Update the SELECT to also fetch status
content = content.replace(
    '"SELECT pam_no FROM pam_records WHERE id=? AND company_id=?", (pam_id, company_id)',
    '"SELECT pam_no, status FROM pam_records WHERE id=? AND company_id=?", (pam_id, company_id)'
)

# After conn.commit() and conn.close(), check if we need to complete it
# Find conn.close()
#     conn.commit()
#     conn.close()
# 
#     # total_amount/tanggal_bayar may have changed on an already-synced SETF PAM.
#     sync_pam_to_bank_setf(pam_id)
# 
#     return {"ok": True, "pesan": "Berhasil memperbarui PAM dan data Payment Application."}

new_tail = """    conn.commit()
    conn.close()

    # If tanggal_bayar is provided and PAM is not yet complete, auto-complete it!
    tgl_bayar = pam_data.get("tanggal_bayar", "").strip()
    if tgl_bayar and pam["status"] != "complete":
        # set_pam_complete_cascade will handle setting status to complete and cascading to PA tables
        set_pam_complete_cascade(pam_id, tgl_bayar, company_id)

    # total_amount/tanggal_bayar may have changed on an already-synced SETF PAM.
    sync_pam_to_bank_setf(pam_id)"""

content = content.replace("""    conn.commit()
    conn.close()

    # total_amount/tanggal_bayar may have changed on an already-synced SETF PAM.
    sync_pam_to_bank_setf(pam_id)""", new_tail)

with open("app/modules/payment_memo/service.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated successfully")
