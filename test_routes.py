import re
with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    text = f.read()

# Add klasifikasi extraction after pam_no
text = re.sub(
    r'(pam_no\s*=\s*data\.get\("pam_no"\))',
    r'\1\n    klasifikasi = data.get("klasifikasi", "Normal")',
    text
)
# Now I need to pass klasifikasi to the service functions.
# 1. save_pam(company_id, pam_no, tanggal, keterangan, user_email, perusahaan, rows, pillar, tab)
# wait, what are the arguments to save_pam?
