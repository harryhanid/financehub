with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(_PAM_FIELDS = \("keterangan", "requestors_name", "total_amount", "due_date",\s*"pam_date", "tanggal_bayar", "pt", "cost_center", "dpp", "ppn", "others"\))',
    r'_PAM_FIELDS = ("klasifikasi", "keterangan", "requestors_name", "total_amount", "due_date",\n                   "pam_date", "tanggal_bayar", "pt", "cost_center", "dpp", "ppn", "others")',
    text
)

# And when pam_data changes, we must also cascade klasifikasi_pam if it changed?
# Wait, the user said: "walaupun saat ini user hanya edit di form Header."
# This means if they change the Header, does the row `klasifikasi_pam` change too?
# Usually, if you edit a PAM, you expect the rows to match the PAM header.
# "setiap baris siswa (payment_beasiswa) harus ditambahkan kolom klasifikasi_pam untuk menyimpan pilihan user saat di PAM, terpisah dari klasifikasi PA."
# I will add an UPDATE for payment_beasiswa and klaim_medical.

with open("app/modules/payment_memo/service.py", "w", encoding="utf-8") as f:
    f.write(text)
