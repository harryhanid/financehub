import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Remove opacity from Budget backgroundColor
content = content.replace("backgroundColor: color + \"66\",", "backgroundColor: color,")

# Update datalabels for setfRenderStackedGroupedChart
target_datalabels = r'datalabels: \{\n\s*display: function\(context\) \{\n\s*return context\.dataset\.data\[context\.dataIndex\] > 0;\n\s*\},\n\s*color: "white",\n\s*font: \{ size: 9, weight: "bold" \},\n\s*formatter: function\(val\) \{ return setfFmtJutaan\(val\); \}\n\s*\}'

repl_datalabels = """datalabels: {
                      display: function(context) { return context.dataset.data[context.dataIndex] > 0; },
                      color: "#ffffff",
                      textStrokeColor: "rgba(0,0,0,0.6)",
                      textStrokeWidth: 3,
                      font: { size: 9, weight: "bold" },
                      formatter: function(val) { return setfFmtJutaan(val); }
                  }"""

content = re.sub(target_datalabels, repl_datalabels, content)

# Update datalabels for setfRenderBudgetVsRealisasiChart (optional, but good for consistency)
# Currently it has:
#           datalabels: {
#             anchor: "end",
#             align: "top",
#             color: setfThemeColor("--text-primary", "#e2e8f0"),
#             font: { size: 10, weight: "600" },
#             formatter: setfDatalabelFormatter,
#           },
# But this draws it ABOVE the bar, so it's already visible. 
# Wait, setfRenderBudgetVsRealisasiChart has two instances of datalabels (for the Kategori/Pillar charts).
# Let's leave them alone because they are above the bar.
# But wait, what if they meant the totals above the bar are hard to read?
# Let's add stroke to setfStackTotalPlugin as well!

target_plugin = r"ctx\.font = 'bold 10px sans-serif';\n\s*ctx\.fillStyle = isDark \? \"#e2e8f0\" : \"#475569\";"
repl_plugin = """ctx.font = 'bold 10px sans-serif';
      ctx.fillStyle = isDark ? "#e2e8f0" : "#475569";
      ctx.strokeStyle = isDark ? "rgba(0,0,0,0.5)" : "rgba(255,255,255,0.7)";
      ctx.lineWidth = 2;"""

content = re.sub(target_plugin, repl_plugin, content)

# And in setfStackTotalPlugin where it draws text:
target_fillText = r"ctx\.fillText\(([^,]+), ([^,]+), ([^\)]+)\);"
repl_fillText = """ctx.strokeText(\\1, \\2, \\3);
            ctx.fillText(\\1, \\2, \\3);"""
content = re.sub(target_fillText, repl_fillText, content)


with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated coloring and datalabels!")
