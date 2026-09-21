with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "r", encoding="utf-8") as f:
    content = f.read()

if "js/app.js" not in content:
    content = content.replace("<script src=\"{{ url_for('static', filename='js/sahabat_etf.js') }}?v=6.000\"></script>", "<script src=\"{{ url_for('static', filename='js/app.js') }}\"></script>\n<script src=\"{{ url_for('static', filename='js/sahabat_etf.js') }}?v=6.000\"></script>")

with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Added app.js")
