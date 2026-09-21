with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "r", encoding="utf-8") as f:
    content = f.read()

old_link = """<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">"""
new_link = """<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">"""

content = content.replace(old_link, new_link)

with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Added style.css to public_index.html")
