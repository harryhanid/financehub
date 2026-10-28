with open("app/modules/sponsorship/routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(185, 205):
    if i < len(lines):
        print(f"{i+1}: {lines[i].rstrip()}")
