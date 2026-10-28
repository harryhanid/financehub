with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

open_braces = 0
found_start = -1
found_end = -1

for i in range(len(lines)):
    if "function ipayAddRow" in lines[i]:
        found_start = i
        open_braces = 0
    if found_start != -1:
        if "{" in lines[i]: open_braces += lines[i].count("{")
        if "}" in lines[i]: open_braces -= lines[i].count("}")
        if open_braces == 0 and "{" in lines[found_start]:
            found_end = i
            break

print("Start:", found_start + 1, "End:", found_end + 1 if found_end != -1 else "NOT FOUND")
