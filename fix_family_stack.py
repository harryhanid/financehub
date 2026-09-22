import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'const budgets = data\.families\.map\(function\(f\) \{ return f\.total_budget \|\| 0; \}\);\s*const realisasis = data\.families\.map\(function\(f\) \{ return f\.total_realisasi \|\| 0; \}\);\s*setfRenderBudgetVsRealisasiChart\("chart-keluarga", xLabels, budgets, realisasis\);'
replacement = """const kesBudget = [];
        const kesActual = [];
        const penBudget = [];
        const penActual = [];

        data.families.forEach(function(f) {
           let kb = 0, ka = 0, pb = 0, pa = 0;
           f.members.forEach(function(m) {
               if (m.kategori && m.kategori.includes("By Medical")) {
                   kb += m.budget || 0;
                   ka += m.realisasi || 0;
               } else {
                   pb += m.budget || 0;
                   pa += m.realisasi || 0;
               }
           });
           kesBudget.push(kb);
           kesActual.push(ka);
           penBudget.push(pb);
           penActual.push(pa);
        });

        const stackData = [
            { name: "By Medical", budget: kesBudget, realisasi: kesActual },
            { name: "By Pendidikan", budget: penBudget, realisasi: penActual }
        ];

        setfRenderStackedGroupedChart("chart-keluarga", xLabels, stackData, "all");"""

content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
