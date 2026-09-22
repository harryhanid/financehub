import re

file_path = "C:/Financehub/app/templates/beasiswa/index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'<script src="\{\{ url_for\(\'static\', filename=\'js/sahabat_etf\.js\'\) \}\}(?:\?v=[0-9\.]+)?"></script>'
replacement = """<script src="{{ url_for('static', filename='js/sahabat_etf.js') }}?v=4.33"></script>"""

content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
