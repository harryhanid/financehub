import os

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

# 1. Remove the injected katTitle and thead blocks
bad_kat = """  const katTitle = document.querySelector("#setf-tahunan-kategori-table").closest('.budget-chart-card').querySelector('h3');
  if(katTitle) katTitle.textContent = 'Budget vs Actual per Kategori (Tabel)';

  const thead = document.querySelector("#setf-tahunan-kategori-table thead");
  if(thead) thead.innerHTML = '<tr><th>Kategori</th><th class="num-right">Budget</th><th class="num-right">Actual</th><th class="num-right">Sisa</th></tr>';"""

bad_pil = """  const pilTitle = document.querySelector("#setf-tahunan-pillar-table").closest('.budget-chart-card').querySelector('h3');
  if(pilTitle) pilTitle.textContent = 'Budget vs Actual per Pillar (Tabel)';

  const thead = document.querySelector("#setf-tahunan-pillar-table thead");
  if(thead) thead.innerHTML = '<tr><th>Pillar</th><th class="num-right">Budget</th><th class="num-right">Actual</th><th class="num-right">Sisa</th></tr>';"""

js_content = js_content.replace(bad_kat, "")
js_content = js_content.replace(bad_pil, "")

# 2. Add try-catch around TahunanKategori
old_kat_fn = """function setfRenderTahunanKategori() {
  const modeEl = document.querySelector('input[name="setf-tahunan-kat-mode"]:checked');"""

new_kat_fn = """function setfRenderTahunanKategori() {
  try {
  const modeEl = document.querySelector('input[name="setf-tahunan-kat-mode"]:checked');"""

old_kat_end = """  setfRenderCustomYearlyStackedChart(
    "chart-tahunan-kategori",
    "kategori",
    "name",
    mode
  );
}"""

new_kat_end = """  setfRenderCustomYearlyStackedChart(
    "chart-tahunan-kategori",
    "kategori",
    "name",
    mode
  );
  } catch(e) {
    console.error("Error in setfRenderTahunanKategori:", e);
    alert("Error in setfRenderTahunanKategori: " + e.message);
  }
}"""

js_content = js_content.replace(old_kat_fn, new_kat_fn)
js_content = js_content.replace(old_kat_end, new_kat_end)

# 3. Add try-catch around TahunanPillar
old_pil_fn = """function setfRenderTahunanPillar() {
  const modeEl = document.querySelector('input[name="setf-tahunan-pil-mode"]:checked');"""

new_pil_fn = """function setfRenderTahunanPillar() {
  try {
  const modeEl = document.querySelector('input[name="setf-tahunan-pil-mode"]:checked');"""

old_pil_end = """  setfRenderCustomYearlyStackedChart(
    "chart-tahunan-pillar",
    "pillar",
    "name",
    mode
  );
}"""

new_pil_end = """  setfRenderCustomYearlyStackedChart(
    "chart-tahunan-pillar",
    "pillar",
    "name",
    mode
  );
  } catch(e) {
    console.error("Error in setfRenderTahunanPillar:", e);
    alert("Error in setfRenderTahunanPillar: " + e.message);
  }
}"""

js_content = js_content.replace(old_pil_fn, new_pil_fn)
js_content = js_content.replace(old_pil_end, new_pil_end)

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Cleaned up JS")
