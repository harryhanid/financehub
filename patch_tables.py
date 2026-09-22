import os

# 1. Update _panel.html
panel_path = 'app/templates/sahabat_etf/_panel.html'
with open(panel_path, 'r', encoding='utf-8') as f:
    panel_content = f.read()

old_kat = """          <div class="budget-chart-card setf-compact-card" style="margin-bottom: 0;">
            <h3>Trend Actual per Kategori</h3>
            <div class="setf-compact-scroll" style="max-height: 350px;">
              <table id="setf-tahunan-kategori-table" class="budget-table">
                <thead><tr><th>Kategori</th><th class="num-right">Total Actual</th></tr></thead>
                <tbody><tr><td colspan="2" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
              </table>
            </div>
          </div>"""

new_kat = """          <div class="budget-chart-card setf-compact-card" style="margin-bottom: 0;">
            <h3>Budget vs Actual per Kategori (Tabel)</h3>
            <div class="setf-compact-scroll" style="max-height: 350px;">
              <table id="setf-tahunan-kategori-table" class="budget-table">
                <thead><tr><th>Kategori</th><th class="num-right">Budget</th><th class="num-right">Actual</th><th class="num-right">Sisa</th></tr></thead>
                <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
              </table>
            </div>
          </div>"""

panel_content = panel_content.replace(old_kat, new_kat)

old_pil = """          <div class="budget-chart-card setf-compact-card" style="margin-bottom: 0;">
            <h3>Trend Actual per Pillar</h3>
            <div class="setf-compact-scroll" style="max-height: 350px;">
              <table id="setf-tahunan-pillar-table" class="budget-table">
                <thead><tr><th>Pillar</th><th class="num-right">Total Actual</th></tr></thead>
                <tbody><tr><td colspan="2" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
              </table>
            </div>
          </div>"""

new_pil = """          <div class="budget-chart-card setf-compact-card" style="margin-bottom: 0;">
            <h3>Budget vs Actual per Pillar (Tabel)</h3>
            <div class="setf-compact-scroll" style="max-height: 350px;">
              <table id="setf-tahunan-pillar-table" class="budget-table">
                <thead><tr><th>Pillar</th><th class="num-right">Budget</th><th class="num-right">Actual</th><th class="num-right">Sisa</th></tr></thead>
                <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
              </table>
            </div>
          </div>"""

panel_content = panel_content.replace(old_pil, new_pil)

with open(panel_path, 'w', encoding='utf-8') as f:
    f.write(panel_content)

# 2. Update sahabat_etf.js
js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

# Replace Kategori Table generation
old_js_kat = """  let tbodyHtml = "";
  data.kategori.forEach(function(k) {
    const total = k.realisasi.reduce((a,b)=>a+b, 0);
    tbodyHtml += "<tr><td>" + k.name + '</td><td class="num-right">' + setfFmtJutaan(total) + "</td></tr>";
  });
  const grandTotal = data.kategori.reduce((s, k) => s + k.realisasi.reduce((a,b)=>a+b,0), 0);
  tbodyHtml += '<tr style="font-weight:bold"><td>Total</td><td class="num-right">' + setfFmtJutaan(grandTotal) + '</td></tr>';"""

new_js_kat = """  let tbodyHtml = "";
  data.kategori.forEach(function(k) {
    const budget = k.budget.reduce((a,b)=>a+b, 0);
    const actual = k.realisasi.reduce((a,b)=>a+b, 0);
    const sisa = budget - actual;
    tbodyHtml += "<tr><td>" + k.name + '</td><td class="num-right">' + setfFmtJutaan(budget) + '</td><td class="num-right">' + setfFmtJutaan(actual) + '</td>' + setfSisaCell(sisa) + '</tr>';
  });
  const grandBudget = data.kategori.reduce((s, k) => s + k.budget.reduce((a,b)=>a+b,0), 0);
  const grandActual = data.kategori.reduce((s, k) => s + k.realisasi.reduce((a,b)=>a+b,0), 0);
  const grandSisa = grandBudget - grandActual;
  tbodyHtml += '<tr style="font-weight:bold"><td>Total</td><td class="num-right">' + setfFmtJutaan(grandBudget) + '</td><td class="num-right">' + setfFmtJutaan(grandActual) + '</td>' + setfSisaCell(grandSisa) + '</tr>';"""

js_content = js_content.replace(old_js_kat, new_js_kat)

# Replace Pillar Table generation
old_js_pil = """  let tbodyHtml = "";
  data.pillar.forEach(function(k) {
    const total = k.realisasi.reduce((a,b)=>a+b, 0);
    tbodyHtml += "<tr><td>" + k.name + '</td><td class="num-right">' + setfFmtJutaan(total) + "</td></tr>";
  });
  const grandTotal = data.pillar.reduce((s, k) => s + k.realisasi.reduce((a,b)=>a+b,0), 0);
  tbodyHtml += '<tr style="font-weight:bold"><td>Total</td><td class="num-right">' + setfFmtJutaan(grandTotal) + '</td></tr>';"""

new_js_pil = """  let tbodyHtml = "";
  data.pillar.forEach(function(k) {
    const budget = k.budget.reduce((a,b)=>a+b, 0);
    const actual = k.realisasi.reduce((a,b)=>a+b, 0);
    const sisa = budget - actual;
    tbodyHtml += "<tr><td>" + k.name + '</td><td class="num-right">' + setfFmtJutaan(budget) + '</td><td class="num-right">' + setfFmtJutaan(actual) + '</td>' + setfSisaCell(sisa) + '</tr>';
  });
  const grandBudget = data.pillar.reduce((s, k) => s + k.budget.reduce((a,b)=>a+b,0), 0);
  const grandActual = data.pillar.reduce((s, k) => s + k.realisasi.reduce((a,b)=>a+b,0), 0);
  const grandSisa = grandBudget - grandActual;
  tbodyHtml += '<tr style="font-weight:bold"><td>Total</td><td class="num-right">' + setfFmtJutaan(grandBudget) + '</td><td class="num-right">' + setfFmtJutaan(grandActual) + '</td>' + setfSisaCell(grandSisa) + '</tr>';"""

js_content = js_content.replace(old_js_pil, new_js_pil)

# Replace skeleton rows
js_content = js_content.replace("skeletonRows(3, 2)", "skeletonRows(3, 4)")

# Replace colspan=2 with colspan=4 in the empty state
js_content = js_content.replace("colspan=\\\"2\\\"", "colspan=\\\"4\\\"")

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Tables updated")
