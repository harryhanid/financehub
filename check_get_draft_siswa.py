with open("app/modules/etf_payment_application/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def get_draft_siswa" in line:
        for j in range(i, min(i+40, len(lines))):
            print(lines[j].rstrip())
        break
