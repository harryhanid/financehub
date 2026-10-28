with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
open_braces = 0
for i in range(5162, 5265):
    line = lines[i]
    if "{" in line: open_braces += line.count("{")
    if "}" in line: open_braces -= line.count("}")
print("Open braces at 5265:", open_braces)
