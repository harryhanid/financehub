import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'setfRenderStackedBarChart\("chart-keluarga", data\.families\);'
replacement = """
      const xLabels = data.families.map(function (f) {
        if (f.members.length > 1) {
          return [f.label, f.members.map(function (m) { return setfFirstName(m.nama); }).join(", ")];
        }
        return setfFirstName(f.members[0].nama);
      });
      const budgets = data.families.map(function(f) { return f.total_budget || 0; });
      const realisasis = data.families.map(function(f) { return f.total_realisasi || 0; });
      setfRenderBudgetVsRealisasiChart("chart-keluarga", xLabels, budgets, realisasis);
"""
content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
