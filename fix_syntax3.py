file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "plugins: {" in line:
        print(f"Line {i+1}:")
        for j in range(max(0, i-5), i+5):
            print(f"  {j+1}: {lines[j].strip('\n')}")
