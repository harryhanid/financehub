import re

with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

new_func = """function zoomTreeQuery(ratio) {
  if (treeChartInstance) {
    let opt = treeChartInstance.getOption();
    let currentZoom = 1;
    if (opt && opt.series && opt.series.length > 0) {
       currentZoom = opt.series[0].zoom || 1;
    }
    treeChartInstance.setOption({
      series: [{ zoom: currentZoom * ratio }]
    });
  }
}"""

content = re.sub(r'function zoomTreeQuery\(ratio\)\s*\{.*?\}', new_func, content, flags=re.DOTALL)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
