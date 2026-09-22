import os, re

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

# For Kategori
kat_pattern = re.compile(r'const labels = data\.years\.map\(y => String\(y\)\);\s*const datasets = \[\];\s*data\.kategori\.forEach[\s\S]*?if\s*\(ctx\)\s*\{\s*setfCharts\["chart-tahunan-kategori"\] = new Chart\(ctx, \{\s*type:\s*"bar"[\s\S]*?\}\);\s*\}')

new_kategori = 'setfRenderCustomYearlyStackedChart("chart-tahunan-kategori", "kategori", "name", mode);'

js_content, count1 = kat_pattern.subn(new_kategori, js_content)
print(f"Replaced {count1} instances of Kategori chart logic.")

# For Pillar
pil_pattern = re.compile(r'const labels = data\.years\.map\(y => String\(y\)\);\s*const datasets = \[\];\s*data\.pillar\.forEach[\s\S]*?if\s*\(ctx\)\s*\{\s*setfCharts\["chart-tahunan-pillar"\] = new Chart\(ctx, \{\s*type:\s*"bar"[\s\S]*?\}\);\s*\}')

new_pillar = 'setfRenderCustomYearlyStackedChart("chart-tahunan-pillar", "pillar", "name", mode);'

js_content, count2 = pil_pattern.subn(new_pillar, js_content)
print(f"Replaced {count2} instances of Pillar chart logic.")

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Done patching v2.")
