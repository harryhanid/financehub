import re

with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

old_zoom = """function zoomTreeQuery(ratio) {
  if (treeChartInstance) {
    treeChartInstance.dispatchAction({
      type: 'roam',
      zoom: ratio
    });
  }
}"""

new_zoom = """function zoomTreeQuery(ratio) {
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

if old_zoom in content:
    content = content.replace(old_zoom, new_zoom)
    with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated zoomTreeQuery back to setOption!")
else:
    print("Could not find dispatchAction zoomTreeQuery block!")
