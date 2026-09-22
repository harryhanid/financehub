import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'function setfRenderYearlyChart\(yearly\) \{.*?\n  \}'

replacement = """function setfRenderTotalTable(tableId, dataList, years) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    let thead = table.querySelector("thead");
    if (!thead) {
        thead = table.createTHead();
    }
    let tbody = table.querySelector("tbody");
    if (!tbody) {
        tbody = table.createTBody();
    }
    
    // Default or empty state
    if (!dataList || !dataList.length || !years || !years.length) {
      thead.innerHTML = "<tr><th>Deskripsi</th><th>Total</th></tr>";
      tbody.innerHTML = "<tr><td colspan='2' style='text-align:center;color:var(--text-muted)'>Belum ada data.</td></tr>";
      return;
    }
    
    // Build Dynamic Thead
    let theadHtml = "<tr><th>Deskripsi</th>";
    years.forEach(function(y) {
       theadHtml += `<th class="num-right">${y}</th>`;
    });
    theadHtml += "<th class='num-right'>Total</th></tr>";
    
    thead.innerHTML = theadHtml;
    thead.style.display = "table-header-group";
    thead.style.visibility = "visible";
    
    let tbodyHtml = "";
    let grandRealisasi = 0;
    
    let grandYearlyRealisasi = new Array(years.length).fill(0);
    let maxPerYear = new Array(years.length).fill(0);

    dataList.forEach(function(item) {
       item.realisasi.forEach(function(val, idx) {
           if ((val || 0) > maxPerYear[idx]) maxPerYear[idx] = val;
       });
    });
    
    dataList.forEach(function(item) {
       const totalRealisasi = item.realisasi.reduce((a, b) => a + (b||0), 0);
       grandRealisasi += totalRealisasi;
       
       let nameHtml = item.name;
       if (tableId.includes("kategori")) nameHtml = setfCatBadge(item.name);
       else if (tableId.includes("pillar")) nameHtml = setfPillarBadge(item.name);
       
       let rowHtml = "<tr><td>" + nameHtml + "</td>";
       
       item.realisasi.forEach(function(val, idx) {
           grandYearlyRealisasi[idx] += (val || 0);
           let v = val || 0;
           let tdStyle = "";
           if (v > 0 && v === maxPerYear[idx]) {
               tdStyle = " style='font-weight:bold; color:var(--positive, #10b981); background:rgba(16, 185, 129, 0.1); border-radius: 4px;'";
           }
           rowHtml += "<td class='num-right'" + tdStyle + ">" + setfFmtJutaan(v) + "</td>";
       });
       rowHtml += "<td class='num-right' style='font-weight:bold;'>" + setfFmtJutaan(totalRealisasi) + "</td></tr>";
       tbodyHtml += rowHtml;
    });
    
    let totalRowHtml = "<tr style='font-weight:bold; background:var(--bg-secondary)'><td>Total Keseluruhan</td>";
    grandYearlyRealisasi.forEach(function(val) {
       totalRowHtml += "<td class='num-right'>" + setfFmtJutaan(val) + "</td>";
    });
    totalRowHtml += "<td class='num-right'>" + setfFmtJutaan(grandRealisasi) + "</td></tr>";
    
    tbody.innerHTML = tbodyHtml + totalRowHtml;
}

function setfRenderYearlyChart(yearly) {
    if (!yearly || !yearly.years || !yearly.years.length) {
      if (setfCharts["chart-tahunan-kategori"]) { setfCharts["chart-tahunan-kategori"].destroy(); delete setfCharts["chart-tahunan-kategori"]; }
      if (setfCharts["chart-tahunan-pillar"]) { setfCharts["chart-tahunan-pillar"].destroy(); delete setfCharts["chart-tahunan-pillar"]; }
      setfRenderTotalTable("setf-tahunan-kategori-table", [], []);
      setfRenderTotalTable("setf-tahunan-pillar-table", [], []);
      return;
    }
    
    // We get mode from toggles, but fallback to "all" if none selected
    let dispMode = "all";
    const modeToggles = document.querySelectorAll("input[name='setf-tahunan-kat-mode']");
    if (modeToggles && modeToggles.length) {
       modeToggles.forEach(r => { if (r.checked) dispMode = r.value; });
    }
    
    setfRenderStackedGroupedChart("chart-tahunan-kategori", yearly.years, yearly.kategori, dispMode);
    setfRenderStackedGroupedChart("chart-tahunan-pillar", yearly.years, yearly.pillar, dispMode);
    
    setfRenderTotalTable("setf-tahunan-kategori-table", yearly.kategori, yearly.years);
    setfRenderTotalTable("setf-tahunan-pillar-table", yearly.pillar, yearly.years);
}"""

content = re.sub(target, replacement, content, count=1, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
