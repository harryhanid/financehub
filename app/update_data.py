path = r"C:\Financehub\app\templates\sponsorship\data.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
    '<th>Amount Request</th><th>AGRI</th><th>APP</th><th>ENERGY & FINANCE</th><th>PROPERTY</th>',
    '<th>Amount Request</th><th>APP</th><th>ENERGY</th><th>PROPERTY</th><th>AGRI</th>'
).replace(
    '<td>{{ r.agri_amount }}</td><td>{{ r.app_amount }}</td>\n        <td>{{ r.energy_finance_amount }}</td><td>{{ r.property_amount }}</td>',
    '<td>{{ r.app_amount }}</td><td>{{ r.energy_finance_amount }}</td>\n        <td>{{ r.property_amount }}</td><td>{{ r.agri_amount }}</td>'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done data.html")
