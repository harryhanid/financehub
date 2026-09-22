import os

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

# 1. Rename setfRenderKategoriChartCustom to setfRenderCustomBudgetChart
js_content = js_content.replace('function setfRenderKategoriChartCustom(canvasId, kategoriRows) {', 'function setfRenderCustomBudgetChart(canvasId, dataRows, labelKey) {')

# 2. Update mapping logic inside the function
js_content = js_content.replace('const labels = kategoriRows.map(k => k.cat1).concat(["TOTAL"]);', 'const labels = dataRows.map(k => k[labelKey]).concat(["TOTAL"]);')
js_content = js_content.replace('const budgetLeft = kategoriRows.map(k => k.budget).concat([null]);', 'const budgetLeft = dataRows.map(k => k.budget).concat([null]);')
js_content = js_content.replace('const actualLeft = kategoriRows.map(k => k.realisasi).concat([null]);', 'const actualLeft = dataRows.map(k => k.realisasi).concat([null]);')
js_content = js_content.replace('const totalBudget = kategoriRows.reduce((sum, k) => sum + k.budget, 0);', 'const totalBudget = dataRows.reduce((sum, k) => sum + k.budget, 0);')
js_content = js_content.replace('const totalActual = kategoriRows.reduce((sum, k) => sum + k.realisasi, 0);', 'const totalActual = dataRows.reduce((sum, k) => sum + k.realisasi, 0);')
js_content = js_content.replace('const budgetRight = kategoriRows.map(k => null).concat([totalBudget]);', 'const budgetRight = dataRows.map(k => null).concat([totalBudget]);')
js_content = js_content.replace('const actualRight = kategoriRows.map(k => null).concat([totalActual]);', 'const actualRight = dataRows.map(k => null).concat([totalActual]);')

# 3. Update the call for chart-kategori
js_content = js_content.replace('setfRenderKategoriChartCustom("chart-kategori", data.kategori);', 'setfRenderCustomBudgetChart("chart-kategori", data.kategori, "cat1");')

# 4. Update the call for chart-pillar
old_pillar_func = """function setfRenderPillarChart(pillarRows) {
  if (!pillarRows || !pillarRows.length) {
    if (setfCharts["chart-pillar"]) { setfCharts["chart-pillar"].destroy(); delete setfCharts["chart-pillar"]; }
    return;
  }
  setfRenderBarChart("chart-pillar", pillarRows.map(function (p) { return p.pillar; }), [
    { label: "Realisasi", data: pillarRows.map(function (p) { return p.realisasi; }), backgroundColor: "#10b981" },
    { label: "Budget", data: pillarRows.map(function (p) { return p.budget; }), backgroundColor: "#3b82f6" }
  ]);
}"""

new_pillar_func = """function setfRenderPillarChart(pillarRows) {
  if (!pillarRows || !pillarRows.length) {
    if (setfCharts["chart-pillar"]) { setfCharts["chart-pillar"].destroy(); delete setfCharts["chart-pillar"]; }
    return;
  }
  setfRenderCustomBudgetChart("chart-pillar", pillarRows, "pillar");
}"""

if old_pillar_func in js_content:
    js_content = js_content.replace(old_pillar_func, new_pillar_func)
else:
    print("Could not find setfRenderPillarChart")

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Pillar Chart patched")
