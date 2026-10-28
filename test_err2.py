import re
with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

for i, line in enumerate(text.splitlines()):
    if "\\'" in line and "klasifikasi" in line:
        print(f"{i+1}: {line}")
