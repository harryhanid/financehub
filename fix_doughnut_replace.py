import re

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

pattern = re.compile(r'setfRenderDoughnutChart\("chart-kategori"[\s\S]*?setfColorForCategory\(k\.cat1\);\s*}\)\);')

new_call = 'setfRenderKategoriChartCustom("chart-kategori", data.kategori);'

if pattern.search(js_content):
    js_content = pattern.sub(new_call, js_content)
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_content)
    print("Doughnut chart replaced successfully!")
else:
    print("Doughnut chart not found!")

