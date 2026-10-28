with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(5557, 5707):
    if "const hidEtfLineId" in lines[i]:
        print(f"Line {i+1}: {lines[i].strip()}")
