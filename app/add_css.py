with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "r", encoding="utf-8") as f:
    content = f.read()

# Make sure style.css is not already there
if "css/style.css" not in content:
    content = content.replace("<link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/budget.css') }}\">", "<link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/style.css') }}\">\n<link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/budget.css') }}\">")

with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Added style.css")
