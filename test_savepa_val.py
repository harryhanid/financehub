with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "async function ipaySavePa" in line:
        for j in range(i, i+50):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
