file_path = "C:/Financehub/app/templates/sahabat_etf/index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("<script src=\"{{ url_for('static', filename='js/sahabat_etf.js') }}\"></script>", "")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Removed duplicate script tag!")
