with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("<link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/style.css') }}\"><link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/style.css') }}\">", "<link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/style.css') }}\">")

with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "w", encoding="utf-8") as f:
    f.write(content)
