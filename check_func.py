with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "function klaimAddSiswa()" in line:
        print(f"klaimAddSiswa starts at {i+1}")
