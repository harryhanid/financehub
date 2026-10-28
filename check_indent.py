with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(995, 1015):
    print(f"Line {i+1}: {lines[i].rstrip()}")
