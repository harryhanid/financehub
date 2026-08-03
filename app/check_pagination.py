path_routes = r"C:\Financehub\app\modules\sponsorship\routes.py"
with open(path_routes, "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "pagination" in line.lower() or "url_for" in line:
        print(f"{i+1}: {line.strip()}")
