with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in [5258, 5632, 5721]:
    # Check if they are inside a function by finding the nearest preceding "function" line
    for j in range(i-1, -1, -1):
        if "function" in lines[j] and not "}" in lines[j]:
            print(f"Line {i} is inside: {lines[j].strip()}")
            break
