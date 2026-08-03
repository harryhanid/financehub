path = r"C:\Financehub\app\modules\sponsorship\service.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# For count_transaksi
c = c.replace(
    '    if filters.get("cat1"):\n        query += " AND cat1 = ?"\n        params.append(filters["cat1"])',
    '    if filters.get("cat1"):\n        query += " AND cat1 = ?"\n        params.append(filters["cat1"])\n    if filters.get("cat2"):\n        query += " AND cat2 = ?"\n        params.append(filters["cat2"])'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done service.py")
