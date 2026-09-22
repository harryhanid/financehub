file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

import re

target = r"""      let labels = data\.kategori\.map\(function \(k\) \{ return k\.cat1 \|\| "Tanpa Kategori"; \}\);\s*let budgets = data\.kategori\.map\(function \(k\) \{ return k\.budget; \}\);\s*let realisasis = data\.kategori\.map\(function \(k\) \{ return k\.realisasi; \}\);\s*let totalBudget = budgets\.reduce\(\(a, b\) => a \+ b, 0\);\s*let totalRealisasi = realisasis\.reduce\(\(a, b\) => a \+ b, 0\);\s*labels\.push\("Total"\);\s*budgets\.push\(totalBudget\);\s*realisasis\.push\(totalRealisasi\);\s*setfRenderBudgetVsRealisasiChart\("chart-kategori", labels, budgets, realisasis\);"""

repl = """      let catLabels = data.kategori.map(function (k) { return k.cat1 || "Tanpa Kategori"; });
      let catBudgets = data.kategori.map(function (k) { return k.budget; });
      let catRealisasis = data.kategori.map(function (k) { return k.realisasi; });
      setfRenderBudgetVsRealisasiChart("chart-kategori", catLabels, catBudgets, catRealisasis);
      
      let pillarLabels = data.pillar.map(function(p) { return p.pillar; });
      let pillarBudgets = data.pillar.map(function(p) { return p.budget; });
      let pillarRealisasis = data.pillar.map(function(p) { return p.realisasi; });
      setfRenderBudgetVsRealisasiChart("chart-pillar", pillarLabels, pillarBudgets, pillarRealisasis);"""

new_content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)
print("Updated fetch block!")
