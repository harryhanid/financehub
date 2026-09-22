import os

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

kat_header = """  const tb = document.querySelector("#setf-tahunan-kategori-table tbody");
  const thead = document.querySelector("#setf-tahunan-kategori-table thead");
  if(thead) thead.innerHTML = '<tr><th>Kategori</th><th class="num-right">Budget</th><th class="num-right">Actual</th><th class="num-right">Sisa</th></tr>';"""

pil_header = """  const tb = document.querySelector("#setf-tahunan-pillar-table tbody");
  const thead = document.querySelector("#setf-tahunan-pillar-table thead");
  if(thead) thead.innerHTML = '<tr><th>Pillar</th><th class="num-right">Budget</th><th class="num-right">Actual</th><th class="num-right">Sisa</th></tr>';"""

js_content = js_content.replace('  const tb = document.querySelector("#setf-tahunan-kategori-table tbody");', kat_header)
js_content = js_content.replace('  const tb = document.querySelector("#setf-tahunan-pillar-table tbody");', pil_header)

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Headers patched dynamically in JS")
