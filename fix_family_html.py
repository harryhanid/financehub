import re

file_path = "C:/Financehub/app/templates/sahabat_etf/_panel.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'<thead><tr><th>Sahabat</th><th>Nama</th><th>Kategori Actual</th><th class="num-right">Actual</th></tr></thead>'
replacement = '<thead><tr><th>Sahabat</th><th>Nama</th><th>Kategori</th><th class="num-right">Budget</th><th class="num-right">Actual</th><th class="num-right">Sisa</th></tr></thead>'
content = content.replace(target, replacement)
content = content.replace('colspan="4"', 'colspan="6"')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
