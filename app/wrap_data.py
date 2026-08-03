path = r"C:\Financehub\app\templates\sponsorship\data.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
    '<table class="budget-table">',
    '<div class="budget-table-container">\n  <table class="budget-table">'
).replace(
    '  </table>\n  <!-- Pagination -->',
    '  </table>\n  </div>\n  <!-- Pagination -->'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done data.html")
