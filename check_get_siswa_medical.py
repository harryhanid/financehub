with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def get_siswa_medical" in line:
        for j in range(i, min(i+25, len(lines))):
            print(lines[j].rstrip())
        break
