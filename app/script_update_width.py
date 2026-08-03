path = r"C:\Financehub\app\modules\sponsorship\exports.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Replace column width
c = c.replace('ws.column_dimensions["G"].width = 43', 'ws.column_dimensions["G"].width = 22.08')

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done")
