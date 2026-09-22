import os

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

kat_title_js = """
  const katTitle = document.querySelector("#setf-tahunan-kategori-table").closest('.budget-chart-card').querySelector('h3');
  if(katTitle) katTitle.textContent = 'Budget vs Actual per Kategori (Tabel)';
"""

pil_title_js = """
  const pilTitle = document.querySelector("#setf-tahunan-pillar-table").closest('.budget-chart-card').querySelector('h3');
  if(pilTitle) pilTitle.textContent = 'Budget vs Actual per Pillar (Tabel)';
"""

# Insert right before generating the table
js_content = js_content.replace('  const thead = document.querySelector("#setf-tahunan-kategori-table thead");', kat_title_js + '\n  const thead = document.querySelector("#setf-tahunan-kategori-table thead");')
js_content = js_content.replace('  const thead = document.querySelector("#setf-tahunan-pillar-table thead");', pil_title_js + '\n  const thead = document.querySelector("#setf-tahunan-pillar-table thead");')

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Titles patched dynamically")
