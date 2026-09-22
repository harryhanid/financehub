import re

file_path = "C:/Financehub/app/templates/sahabat_etf/index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>'
replacement = """<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/patternomaly@1.3.2/dist/patternomaly.min.js"></script>"""

content = re.sub(target, replacement, content)
content = re.sub(r'sahabat_etf\.js\?v=4\.30', 'sahabat_etf.js?v=4.31', content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
