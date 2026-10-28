with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "function klaimAddSiswa" in line:
        for j in range(i, min(len(lines), i+150)):
            print(f"Line {j+1}: {lines[j].rstrip()}")
            if "appendChild(tr)" in lines[j]:
                break
        break
