with open("rendered.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "const CAT2 =" in line:
        print(f"Line {i+1}: {line.strip()}")
