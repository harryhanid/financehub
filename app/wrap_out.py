path = r"C:\Financehub\app\templates\sponsorship\outstanding.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
""".outstanding-table th {
  background: #0f4c5c;
  color: #fff;
  text-align: left;
}""",
""".outstanding-table th {
  background: #0f4c5c;
  color: #fff;
  text-align: left;
  position: sticky;
  top: 0;
  z-index: 10;
}"""
)

c = c.replace('<div style="overflow-x: auto;">', '<div class="budget-table-container">')

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done outstanding.html")
