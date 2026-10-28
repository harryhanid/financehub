with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(5162, 5212):
    if "apiFetch" in lines[i] or "oninput =" in lines[i]:
        print(f"Line {i+1}: {lines[i].rstrip()}")
