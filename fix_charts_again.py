import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'setfRenderDoughnutChart\("chart-kategori",\s*data.kategori.map\(function \(k\) \{ return k.cat1; \}\),\s*data.kategori.map\(function \(k\) \{ return k.realisasi; \}\),\s*data.kategori.map\(function \(k\) \{ return setfColorForCategory\(k.cat1\); \}\)\);'

replacement = """setfRenderBudgetVsRealisasiChart("chart-kategori",
          data.kategori.map(function (k) { return k.cat1; }),
          data.kategori.map(function (k) { return k.budget; }),
          data.kategori.map(function (k) { return k.realisasi; }),
          setfSetKategoriDrilldown
        );
        if (data.pillar) {
            setfRenderBudgetVsRealisasiChart("chart-pillar",
              data.pillar.map(function (p) { return p.pillar; }),
              data.pillar.map(function (p) { return p.budget; }),
              data.pillar.map(function (p) { return p.realisasi; })
            );
        }"""

content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
