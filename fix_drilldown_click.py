import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'options: \{\s*responsive: true,\s*layout: \{ padding: \{ top: 20, bottom: 25 \} \},'
repl = """options: {
            responsive: true,
            layout: { padding: { top: 20, bottom: 25 } },
            onClick: function (evt, elements) {
                if (!elements.length) return;
                const idx = elements[0].index;
                const clickedLabel = dual.labels[idx];
                if (clickedLabel !== "TOTAL" && canvasId === "chart-kategori") {
                    setfSetKategoriDrilldown(clickedLabel);
                }
            },"""
content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Injected onClick handler for Drilldown!")
