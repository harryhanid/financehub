import os

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

bad_filter = """            filter: function(item, chart) {
               const ds = chart.data.datasets[item.datasetIndex];
               return !ds.hiddenLegend;
            }"""

good_filter = """            filter: function(item, data) {
               const ds = data.datasets[item.datasetIndex];
               return !ds.hiddenLegend;
            }"""

if bad_filter in js_content:
    js_content = js_content.replace(bad_filter, good_filter)
else:
    print("WARNING: bad filter not found")

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Legend filter patched")
