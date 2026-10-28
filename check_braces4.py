with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
open_braces = 0
found_end = -1
for i in range(5162, len(lines)):
    line = lines[i]
    if "{" in line: open_braces += line.count("{")
    if "}" in line: open_braces -= line.count("}")
    if open_braces == 0 and "{" in lines[5162]:
        found_end = i
        break
print("ipayAddRow ends at line:", found_end + 1 if found_end != -1 else "NOT FOUND")
