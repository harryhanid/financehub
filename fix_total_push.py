import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'let catLabels = data\.kategori\.map\(function \(k\) \{ return k\.cat1 \|\| "Tanpa Kategori"; \}\);\s*let catBudgets = data\.kategori\.map\(function \(k\) \{ return k\.budget; \}\);\s*let catRealisasis = data\.kategori\.map\(function \(k\) \{ return k\.realisasi; \}\);\s*setfRenderBudgetVsRealisasiChart\("chart-kategori", catLabels, catBudgets, catRealisasis\);\s*let pillarLabels = data\.pillar\.map\(function\(p\) \{ return p\.pillar; \}\);\s*let pillarBudgets = data\.pillar\.map\(function\(p\) \{ return p\.budget; \}\);\s*let pillarRealisasis = data\.pillar\.map\(function\(p\) \{ return p\.realisasi; \}\);\s*setfRenderBudgetVsRealisasiChart\("chart-pillar", pillarLabels, pillarBudgets, pillarRealisasis\);'

repl = """      let catLabels = data.kategori.map(function (k) { return k.cat1 || "Tanpa Kategori"; });
      let catBudgets = data.kategori.map(function (k) { return k.budget; });
      let catRealisasis = data.kategori.map(function (k) { return k.realisasi; });
      let catB = catBudgets.reduce((a,b)=>a+b,0);
      let catR = catRealisasis.reduce((a,b)=>a+b,0);
      catLabels.push("TOTAL"); catBudgets.push(catB); catRealisasis.push(catR);
      setfRenderBudgetVsRealisasiChart("chart-kategori", catLabels, catBudgets, catRealisasis);
      
      let pillarLabels = data.pillar.map(function(p) { return p.pillar; });
      let pillarBudgets = data.pillar.map(function(p) { return p.budget; });
      let pillarRealisasis = data.pillar.map(function(p) { return p.realisasi; });
      let pilB = pillarBudgets.reduce((a,b)=>a+b,0);
      let pilR = pillarRealisasis.reduce((a,b)=>a+b,0);
      pillarLabels.push("TOTAL"); pillarBudgets.push(pilB); pillarRealisasis.push(pilR);
      setfRenderBudgetVsRealisasiChart("chart-pillar", pillarLabels, pillarBudgets, pillarRealisasis);"""

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Injected TOTAL pushing logic!")
