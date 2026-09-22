import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. setfPillarBadge
content = content.replace("""  function setfCatBadgeList(kategoriCsv) {
    if (!kategoriCsv) return "";
    return kategoriCsv.split(",").map(function (c) { return setfCatBadge(c.trim()); }).join(" ");
  }
  
  const SETF_STATUS_BADGE_CLASS = {""", """  function setfCatBadgeList(kategoriCsv) {
    if (!kategoriCsv) return "";
    return kategoriCsv.split(",").map(function (c) { return setfCatBadge(c.trim()); }).join(" ");
  }

  const SETF_PILLAR_BADGE_CLASS = {
    "AGRI": "badge-pil-agri",
    "APP": "badge-pil-app",
    "FINANCE": "badge-pil-finance",
    "SETF": "badge-pil-setf",
  };
  function setfPillarBadge(pillar) {
    if (!pillar) return "";
    const cls = SETF_PILLAR_BADGE_CLASS[pillar.toUpperCase()] || "badge-cat-lainnya";
    return "<span class=\\"budget-badge " + cls + "\\">" + pillar + "</span>";
  }
  
  const SETF_STATUS_BADGE_CLASS = {""")

# 2. Use setfPillarBadge in setfRenderPillarTable
content = content.replace('"<td>" + p.pillar + "</td>" +', '"<td>" + setfPillarBadge(p.pillar) + "</td>" +')
content = content.replace('const totalSisa = pillarRows.reduce(function (s, p) { return s + p.sisa; }, 0);', '')
content = content.replace('setfSisaCell(totalSisa) + "</tr>";', 'setfSisaCell(totalBudget - totalRealisasi) + "</tr>";')

# 3. Use setfPillarBadge in setfRenderLaporanPillarBreakdown
content = content.replace('html += \'<tr class="setf-laporan-subtotal-row"><td colspan="3">\' + p.pillar_label + \'</td>\' +', 'html += \'<tr class="setf-laporan-subtotal-row"><td colspan="3">\' + setfPillarBadge(p.pillar_label) + \'</td>\' +')

# 4. Deskripsi
content = content.replace('thead.innerHTML = "<tr><th>Nama</th><th>Total</th></tr>";', 'thead.innerHTML = "<tr><th>Deskripsi</th><th>Total</th></tr>";')
content = content.replace('let theadHtml = "<tr><th>Nama</th>";', 'let theadHtml = "<tr><th>Deskripsi</th>";')

# 5. Trend Max Highlight and Badges
old_trend = """      // Arrays to store total actual per year
      let grandYearlyRealisasi = new Array(years.length).fill(0);
      
      dataList.forEach(function(item) {
         const totalRealisasi = item.realisasi.reduce((a, b) => a + (b||0), 0);
         grandRealisasi += totalRealisasi;
         
         let rowHtml = "<tr><td>" + item.name + "</td>";
         
         // Yearly actuals
         item.realisasi.forEach(function(val, idx) {
             grandYearlyRealisasi[idx] += (val || 0);
             rowHtml += "<td class='num-right'>" + setfFmtJutaan(val || 0) + "</td>";
         });"""

new_trend = """      let grandYearlyRealisasi = new Array(years.length).fill(0);
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
         });"""
content = content.replace(old_trend, new_trend)

# 6. customLabelsPlugin for StackedGroupedChart (Top Totals)
old_bottomLabels = """  const bottomLabelsPlugin = {
    id: 'bottomLabels',
    afterDatasetsDraw: function(chart) {
      if (displayMode !== "all") return;
      const ctx = chart.ctx;
      ctx.save();
      ctx.font = "10px Inter, sans-serif";
      ctx.fillStyle = isDark ? "#94a3b8" : "#64748b";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      
      const yAxis = chart.scales.y;
      
      chart.data.labels.forEach((_, index) => {
        let metaB = chart.getDatasetMeta(0);
        let metaR = chart.getDatasetMeta(1);
        
        if (metaB && metaB.data[index]) {
           let xB = metaB.data[index].x;
           ctx.fillText("Budget", xB, yAxis.bottom + 6);
        }
        if (metaR && metaR.data[index]) {
           let xR = metaR.data[index].x;
           ctx.fillText("Realisasi", xR, yAxis.bottom + 6);
        }
      });
      ctx.restore();
    }
  };"""

new_customLabels = """  const customLabelsPlugin = {
    id: 'customLabels',
    afterDatasetsDraw: function(chart) {
      const ctx = chart.ctx;
      ctx.save();
      const yAxis = chart.scales.y;
      const totals = {}; 
      
      chart.data.labels.forEach((_, i) => totals[i] = {});
      
      chart.data.datasets.forEach((ds, dsIndex) => {
         const meta = chart.getDatasetMeta(dsIndex);
         if (meta.hidden) return;
         const stackId = meta.stack; 
         
         meta.data.forEach((bar, i) => {
            if (!totals[i][stackId]) totals[i][stackId] = { sum: 0, x: bar.x };
            totals[i][stackId].sum += (ds.data[i] || 0);
            totals[i][stackId].x = bar.x; 
         });
      });
      
      chart.data.labels.forEach((_, index) => {
        ctx.font = "bold 10px Inter, sans-serif";
        ctx.fillStyle = isDark ? "#e2e8f0" : "#475569";
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        
        Object.keys(totals[index]).forEach(stackId => {
           const info = totals[index][stackId];
           if (info.sum > 0) {
              ctx.fillText(setfFmtJutaan(info.sum), info.x, yAxis.getPixelForValue(info.sum) - 4);
           }
        });
        
        if (displayMode === "all") {
            ctx.font = "10px Inter, sans-serif";
            ctx.fillStyle = isDark ? "#94a3b8" : "#64748b";
            ctx.textBaseline = "top";
            let metaB = chart.getDatasetMeta(0);
            let metaR = chart.getDatasetMeta(1);
            if (metaB && metaB.data[index]) ctx.fillText("Budget", metaB.data[index].x, yAxis.bottom + 6);
            if (metaR && metaR.data[index]) ctx.fillText("Realisasi", metaR.data[index].x, yAxis.bottom + 6);
        }
      });
      ctx.restore();
    }
  };"""

content = content.replace(old_bottomLabels, new_customLabels)
content = content.replace("plugins: [ChartDataLabels, bottomLabelsPlugin]", "plugins: [ChartDataLabels, customLabelsPlugin]")


# 7. StackedBarChart for Sahabat families
target_regex = r"function setfRenderStackedBarChart\(canvasId, families\).*?scales: \{.*?\}\s*\}\s*\}\s*\);\s*\}"

replacement = """function setfRenderStackedBarChart(canvasId, families) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";

  function hexToRgba(hex, alpha) {
      if (!hex || hex === "light") return "rgba(0,0,0,0)";
      const h = hex.replace("#", "");
      if (h.length === 3) return `rgba(${parseInt(h[0]+h[0],16)}, ${parseInt(h[1]+h[1],16)}, ${parseInt(h[2]+h[2],16)}, ${alpha})`;
      return `rgba(${parseInt(h.slice(0,2),16)}, ${parseInt(h.slice(2,4),16)}, ${parseInt(h.slice(4,6),16)}, ${alpha})`;
  }

  const maxMembers = families.reduce(function (m, f) { return Math.max(m, f.members.length); }, 0);
  const datasets = [];
  for (let i = 0; i < maxMembers; i++) {
    const fill = SETF_PALETTE[i % SETF_PALETTE.length];
    
    datasets.push({
      label: "Anggota " + (i + 1) + " (Budget)",
      data: families.map(function (f) { return i < f.members.length ? f.members[i].budget : null; }),
      backgroundColor: hexToRgba(fill, 0.4),
      borderColor: fill,
      borderWidth: 1,
      borderSkipped: false,
      stack: "Budget"
    });

    datasets.push({
      label: "Anggota " + (i + 1) + " (Actual)",
      data: families.map(function (f) { return i < f.members.length ? f.members[i].realisasi : null; }),
      backgroundColor: fill,
      borderColor: setfShadeColor(fill, -25),
      borderWidth: 2,
      borderSkipped: false,
      stack: "Realisasi"
    });
  }

  const xLabels = families.map(function (f) {
    if (f.members.length > 1) {
      return [f.label, f.members.map(function (m) { return setfFirstName(m.nama); }).join(", ")];
    }
    return setfFirstName(f.members[0].nama);
  });

  const customKeluargaLabelsPlugin = {
    id: "customKeluargaLabels",
    afterDatasetsDraw: function(chart) {
      const c = chart.ctx;
      c.save();
      const yAxis = chart.scales.y;
      const totals = {}; 
      
      chart.data.labels.forEach((_, i) => totals[i] = {});
      
      chart.data.datasets.forEach((ds, dsIndex) => {
         const meta = chart.getDatasetMeta(dsIndex);
         if (meta.hidden) return;
         const stackId = meta.stack; 
         
         meta.data.forEach((bar, i) => {
            if (!totals[i][stackId]) totals[i][stackId] = { sum: 0, x: bar.x };
            totals[i][stackId].sum += (ds.data[i] || 0);
            totals[i][stackId].x = bar.x; 
         });
      });
      
      chart.data.labels.forEach((_, index) => {
        // Top Totals
        c.font = "bold 10px Inter, sans-serif";
        c.fillStyle = isDark ? "#e2e8f0" : "#475569";
        c.textAlign = "center";
        c.textBaseline = "bottom";
        
        Object.keys(totals[index]).forEach(stackId => {
           const info = totals[index][stackId];
           if (info.sum > 0) {
              c.fillText(setfFmtJutaan(info.sum), info.x, yAxis.getPixelForValue(info.sum) - 4);
           }
        });
        
        // Bottom Labels (Budget / Realisasi)
        c.font = "10px Inter, sans-serif";
        c.fillStyle = isDark ? "#94a3b8" : "#64748b";
        c.textBaseline = "top";
        
        let metaB = chart.getDatasetMeta(0);
        let metaR = chart.getDatasetMeta(1);
        
        if (metaB && metaB.data[index]) {
           c.fillText("Budget", metaB.data[index].x, yAxis.bottom + 6);
        }
        if (metaR && metaR.data[index]) {
           c.fillText("Realisasi", metaR.data[index].x, yAxis.bottom + 6);
        }
      });
      c.restore();
    }
  };

  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: xLabels, datasets: datasets },
    plugins: [ChartDataLabels, customKeluargaLabelsPlugin],
    options: {
      responsive: true,
      layout: { padding: { top: 20 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (item) {
              const memberIdx = Math.floor(item.datasetIndex / 2);
              const isBudget = (item.datasetIndex % 2) === 0;
              const member = families[item.dataIndex].members[memberIdx];
              if (!member) return "";
              const val = isBudget ? member.budget : member.realisasi;
              return member.nama + (isBudget ? " (Budget)" : "") + ": " + setfFmtJutaan(val);
            },
          },
        },
        datalabels: {
          display: function(context) {
             const val = context.dataset.data[context.dataIndex];
             if (!val || val <= 0) return false;
             const meta = context.chart.getDatasetMeta(context.datasetIndex);
             const stackId = meta.stack;
             let sum = 0;
             context.chart.data.datasets.forEach((ds, i) => {
                 const m = context.chart.getDatasetMeta(i);
                 if (m.stack === stackId) {
                     sum += (ds.data[context.dataIndex] || 0);
                 }
             });
             return sum > 0 && (val / sum) > 0.06;
          },
          anchor: "center",
          align: "center",
          color: function(context) {
             const isBudget = (context.datasetIndex % 2) === 0;
             return isBudget ? "#1e293b" : "#fff";
          },
          font: { size: 9, weight: "600" },
          formatter: setfDatalabelFormatter,
        },
      },
      scales: {
        x: { 
            stacked: true, 
            ticks: { color: isDark ? "#94a3b8" : "#64748b" }, 
            grid: { color: isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)" } 
        },
        y: {
          stacked: true,
          ticks: {
            color: isDark ? "#94a3b8" : "#64748b",
            callback: function (value) { return setfFmtJutaan(value); },
          },
          grid: { color: isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)" },
        },
      },
    },
  });
}"""

content = re.sub(target_regex, replacement, content, count=1, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Restored logic.")
