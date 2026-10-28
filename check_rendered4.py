with open("rendered.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(4123, 4133):
    print(f"Line {i+1}: {lines[i].rstrip()}")
