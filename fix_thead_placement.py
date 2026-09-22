import os

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

# For Kategori
bad_kat = """  const katTitle = document.querySelector("#setf-tahunan-kategori-table").closest('.budget-chart-card').querySelector('h3');
  if(katTitle) katTitle.textContent = 'Budget vs Actual per Kategori (Tabel)';

  const thead = document.querySelector("#setf-tahunan-kategori-table thead");
  if(thead) thead.innerHTML = '<tr><th>Kategori</th><th class="num-right">Budget</th><th class="num-right">Actual</th><th class="num-right">Sisa</th></tr>';"""

js_content = js_content.replace(bad_kat, "")

good_kat = """
  const katTitle = document.querySelector("#setf-tahunan-kategori-table").closest('.budget-chart-card').querySelector('h3');
  if(katTitle) katTitle.textContent = 'Budget vs Actual per Kategori (Tabel)';
  const thead_k = document.querySelector("#setf-tahunan-kategori-table thead");
  if(thead_k) thead_k.innerHTML = '<tr><th>Kategori</th><th class="num-right">Budget</th><th class="num-right">Actual</th><th class="num-right">Sisa</th></tr>';
"""
js_content = js_content.replace('function setfRenderTahunanKategori() {', 'function setfRenderTahunanKategori() {' + good_kat)

# For Pillar
bad_pil = """  const pilTitle = document.querySelector("#setf-tahunan-pillar-table").closest('.budget-chart-card').querySelector('h3');
  if(pilTitle) pilTitle.textContent = 'Budget vs Actual per Pillar (Tabel)';

  const thead = document.querySelector("#setf-tahunan-pillar-table thead");
  if(thead) thead.innerHTML = '<tr><th>Pillar</th><th class="num-right">Budget</th><th class="num-right">Actual</th><th class="num-right">Sisa</th></tr>';"""

js_content = js_content.replace(bad_pil, "")

good_pil = """
  const pilTitle = document.querySelector("#setf-tahunan-pillar-table").closest('.budget-chart-card').querySelector('h3');
  if(pilTitle) pilTitle.textContent = 'Budget vs Actual per Pillar (Tabel)';
  const thead_p = document.querySelector("#setf-tahunan-pillar-table thead");
  if(thead_p) thead_p.innerHTML = '<tr><th>Pillar</th><th class="num-right">Budget</th><th class="num-right">Actual</th><th class="num-right">Sisa</th></tr>';
"""
js_content = js_content.replace('function setfRenderTahunanPillar() {', 'function setfRenderTahunanPillar() {' + good_pil)

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Fixed thead placement")
