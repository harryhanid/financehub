with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(# Cascade pam_no rename to all referencing tables\n\s*if pam_no_changed:)',
    r'if "klasifikasi" in pam_data:\n        klas = pam_data["klasifikasi"]\n        curr_pam = new_pam_no if pam_no_changed else old_pam_no\n        conn.execute("UPDATE payment_beasiswa SET klasifikasi_pam=? WHERE pam=? AND company_id=?", (klas, curr_pam, company_id))\n        conn.execute("UPDATE klaim_medical SET klasifikasi_pam=? WHERE pam=? AND company_id=?", (klas, curr_pam, company_id))\n        # pam_transaction_lines doesn\'t have company_id\n        conn.execute("UPDATE pam_transaction_lines SET klasifikasi_pam=? WHERE pam_id=?", (klas, pam_id))\n\n    \1',
    text
)

with open("app/modules/payment_memo/service.py", "w", encoding="utf-8") as f:
    f.write(text)
