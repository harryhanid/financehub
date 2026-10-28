with open("rendered.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(4115, 4135):
    print(f"Line {i+1}: {lines[i].rstrip()}")
