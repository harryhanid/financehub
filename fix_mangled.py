import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'function setfRenderTahunanPillar\(yearly\) \{.*?function setfRenderPillarTable'
replacement = """function setfRenderTahunanPillar(yearly) {
    if (!yearly || !yearly.years || !yearly.years.length) {
      if (setfCharts["chart-tahunan-pillar"]) { setfCharts["chart-tahunan-pillar"].destroy(); delete setfCharts["chart-tahunan-pillar"]; }
      setfRenderTotalTable("setf-tahunan-pillar-table", [], []);
      return;
    }
    let pilMode = "all";
    const selectedPil = document.querySelector('input[name="setf-tahunan-pil-mode"]:checked');
    if (selectedPil) pilMode = selectedPil.value;
    setfRenderStackedGroupedChart("chart-tahunan-pillar", yearly.years, yearly.pillar, pilMode);
    setfRenderTotalTable("setf-tahunan-pillar-table", yearly.pillar, yearly.years, pilMode);
}

function setfRenderPillarTable"""

content = re.sub(target, replacement, content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
