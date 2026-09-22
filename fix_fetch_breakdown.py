import re
file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'fetch\("/beasiswa/sahabat/api/breakdown"\s*\+\s*\(qs\s*\?\s*"\?"\s*\+\s*qs\s*:\s*""\)\)[\s\S]*?\.then\(function\s*\(\s*data\s*\)\s*\{[\s\S]*?\}\)[\s\S]*?\.catch\(function\s*\(\)\s*\{[\s\S]*?\}\);'

repl = """fetch("/beasiswa/sahabat/api/breakdown" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      let catLabels = data.kategori.map(function (k) { return k.cat1 || "Tanpa Kategori"; });
      let catBudgets = data.kategori.map(function (k) { return k.budget; });
      let catRealisasis = data.kategori.map(function (k) { return k.realisasi; });
      
      let pillarLabels = data.pillar.map(function (p) { return p.pillar; });
      let pillarBudgets = data.pillar.map(function (p) { return p.budget; });
      let pillarRealisasis = data.pillar.map(function (p) { return p.realisasi; });
      
      setfRenderBudgetVsRealisasiChart("chart-kategori", catLabels, catBudgets, catRealisasis);
      setfRenderBudgetVsRealisasiChart("chart-pillar", pillarLabels, pillarBudgets, pillarRealisasis);
      
      setfRenderKategoriTable(data.kategori);
      setfRenderExecSummary(data);
      setfRenderYearlyChart(data.yearly);
      setfRenderPillarTable(data.pillar);
    })
    .catch(function (e) { 
      console.error(e);
      showToast("Gagal memuat breakdown kategori.", "error"); 
    });"""

new_content = re.sub(target, repl, content)
if new_content != content:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Fixed fetch block!")
else:
    print("Failed to replace!")
