import re
with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. pam_records insert patch
text = re.sub(
    r'(INSERT INTO pam_records\s*\([^)]+)(company_id)',
    r'\1klasifikasi, \2',
    text
)
text = re.sub(
    r'(VALUES\s*\()(\?)',
    r'\1?, \2',
    text
)

# 2. Extract klasifikasi from data
def add_klasifikasi_extract(match):
    return match.group(0) + '\n    klasifikasi = data.get("klasifikasi", "Normal")'

text = re.sub(
    r'pam_no\s*=\s*\(data\.get\("pam_no"\) or ""\)\.strip\(\)',
    add_klasifikasi_extract,
    text
)

# Wait! The tuple parameters need to be updated.
# I will use a manual script for replacing the tuples for `execute` because it's safer.
with open("patch_temp.py", "w") as out: out.write("")
