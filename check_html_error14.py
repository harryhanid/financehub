with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(5600, 5720):
    if "function klaimAdd" in lines[i] or "}" in lines[i]:
        print(f"Line {i+1}: {lines[i].rstrip()}")
