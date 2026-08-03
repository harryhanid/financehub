exports_path = r"C:\Financehub\app\modules\payment_memo\exports.py"
with open(exports_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
err_line = 1949
start = max(0, err_line - 10)
end = min(len(lines), err_line + 10)
for i in range(start, end):
    print(f"{i+1}: {lines[i].rstrip()}")
