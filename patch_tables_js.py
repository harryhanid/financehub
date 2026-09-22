import sys

def patch_js():
    with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'r', encoding='utf-8') as f:
        content = f.read()

    old_func = """function setfRenderYearlyChart(yearly) {
  if (!yearly || !yearly.years || !yearly.years.length) {
    if (setfCharts["chart-tahunan-kategori"]) { setfCharts["chart-tahunan-kategori"].destroy(); delete setfCharts["chart-tahunan-kategori"]; }
    if (setfCharts["chart-tahunan-pillar"]) { setfCharts["chart-tahunan-pillar"].destroy(); delete setfCharts["chart-tahunan-pillar"]; }
    return;
  }
  setfRenderStackedGroupedChart("chart-tahunan-kategori", yearly.years, yearly.kategori);
  setfRenderStackedGroupedChart("chart-tahunan-pillar", yearly.years, yearly.pillar);
}"""

    new_func = """function setfRenderTotalTable(tableId, dataList) {
  const tbody = document.querySelector("#" + tableId + " tbody");
  if (!tbody) return;
  if (!dataList || !dataList.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Belum ada data.</td></tr>';
    return;
  }
  
  let grandBudget = 0;
  let grandRealisasi = 0;
  
  const rows = dataList.map(function(item) {
     const totalBudget = item.budget.reduce((a, b) => a + (b||0), 0);
     const totalRealisasi = item.realisasi.reduce((a, b) => a + (b||0), 0);
     const sisa = totalBudget - totalRealisasi;
     const pctSisa = totalBudget > 0 ? (sisa / totalBudget) * 100 : 0;
     
     grandBudget += totalBudget;
     grandRealisasi += totalRealisasi;
     
     return "<tr>" + 
       "<td>" + item.name + "</td>" +
       "<td class='num-right'>" + setfFmtJutaan(totalBudget) + "</td>" + 
       "<td class='num-right'>" + setfFmtJutaan(totalRealisasi) + "</td>" + 
       setfSisaCell(sisa) + 
       "<td class='num-right'>" + pctSisa.toFixed(1) + "%</td>" + 
       "</tr>";
  }).join("");
  
  const grandSisa = grandBudget - grandRealisasi;
  const grandPct = grandBudget > 0 ? (grandSisa / grandBudget) * 100 : 0;
  const totalRow = "<tr style='font-weight:bold'>" +
    "<td>Total Keseluruhan</td>" +
    "<td class='num-right'>" + setfFmtJutaan(grandBudget) + "</td>" + 
    "<td class='num-right'>" + setfFmtJutaan(grandRealisasi) + "</td>" + 
    setfSisaCell(grandSisa) + 
    "<td class='num-right'>" + grandPct.toFixed(1) + "%</td>" + 
    "</tr>";
    
  tbody.innerHTML = rows + totalRow;
}

function setfRenderYearlyChart(yearly) {
  if (!yearly || !yearly.years || !yearly.years.length) {
    if (setfCharts["chart-tahunan-kategori"]) { setfCharts["chart-tahunan-kategori"].destroy(); delete setfCharts["chart-tahunan-kategori"]; }
    if (setfCharts["chart-tahunan-pillar"]) { setfCharts["chart-tahunan-pillar"].destroy(); delete setfCharts["chart-tahunan-pillar"]; }
    setfRenderTotalTable("setf-tahunan-kategori-table", []);
    setfRenderTotalTable("setf-tahunan-pillar-table", []);
    return;
  }
  setfRenderStackedGroupedChart("chart-tahunan-kategori", yearly.years, yearly.kategori);
  setfRenderStackedGroupedChart("chart-tahunan-pillar", yearly.years, yearly.pillar);
  
  setfRenderTotalTable("setf-tahunan-kategori-table", yearly.kategori);
  setfRenderTotalTable("setf-tahunan-pillar-table", yearly.pillar);
}"""

    if old_func in content:
        content = content.replace(old_func, new_func)
        with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched sahabat_etf.js successfully")
    else:
        print("Could not find old_func")

if __name__ == '__main__':
    patch_js()
