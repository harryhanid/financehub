with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
old_commit = "    conn.commit()\n    conn.close()"

new_commit = """    
    conn.commit()
    conn.close()

    # Trigger complete cascade if tanggal_bayar is filled and status is not complete
    if "tanggal_bayar" in pam_data and pam_data["tanggal_bayar"]:
        if current_status != 'complete':
            set_pam_complete_cascade(pam_id, pam_data["tanggal_bayar"], company_id)
"""

text = text.replace(old_commit, new_commit, 1)

with open("app/modules/payment_memo/service.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Restored cascade fix")
