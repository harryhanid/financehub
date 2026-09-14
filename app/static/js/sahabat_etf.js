function setfHexToRgba(hex, alpha) {
    let r = parseInt(hex.slice(1, 3), 16),
        g = parseInt(hex.slice(3, 5), 16),
        b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// static/js/sahabat_etf.js
let setfCharts = {};

let setfActiveKategoriDrilldown = null;

function setfExpandGrafik() {
  const details = document.getElementById("setf-grafik-accordion");
  if (!details) return;
  if (!details.open) details.open = true;
}

function setfHighlightMonthlyRow(bulanIndex) {
  setfExpandGrafik();
  const tbody = document.querySelector("#setf-monthly-table tbody");
  if (!tbody) return;
  const rows = tbody.querySelectorAll("tr");
  rows.forEach(function (tr) { tr.classList.remove("setf-row-highlight"); });
  const target = rows[bulanIndex];
  if (target) {
    target.classList.add("setf-row-highlight");
    target.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function setfRenderDrilldownChip() {
  const chip = document.getElementById("setf-drilldown-chip");
  if (!chip) return;
  if (!setfActiveKategoriDrilldown) {
    chip.style.display = "none";
    chip.innerHTML = "";
    return;
  }
  chip.style.display = "inline-flex";
  chip.innerHTML = "Filter aktif: Kategori = " + setfActiveKategoriDrilldown +
    ' <button type="button" class="budget-btn" style="padding:.15rem .6rem;font-size:.72rem" ' +
    'onclick="setfClearKategoriDrilldown()">Hapus filter</button>';
}

function setfRefetchLatestPayments() {
  const filters = setfGetSelectedFilters();
  const params = new URLSearchParams(setfBuildQueryString(filters));
  if (setfActiveKategoriDrilldown) params.set("kategori", setfActiveKategoriDrilldown);
  fetch("/beasiswa/sahabat/api/latest_payments?" + params.toString())
    .then(function (r) { return r.json(); })
    .then(function (data) { setfRenderLatestPaymentsTable(data.rows); })
    .catch(function () { showToast("Gagal memuat 10 transaksi terakhir.", "error"); });
}

function setfSetKategoriDrilldown(kategoriName) {
  setfActiveKategoriDrilldown = kategoriName;
  setfRenderDrilldownChip();
  setfExpandGrafik();
  setfRefetchLatestPayments();
  const table = document.getElementById("setf-latest-payments-table");
  if (table) table.scrollIntoView({ behavior: "smooth", block: "center" });
}

function setfClearKategoriDrilldown() {
  setfActiveKategoriDrilldown = null;
  setfRenderDrilldownChip();
  setfRefetchLatestPayments();
}


const setfGroupedSublabelPlugin = {
    id: 'groupedSublabel',
    afterDraw: function(chart) {
      const ctx = chart.ctx;
      ctx.save();
      const isDark = document.documentElement.getAttribute("data-theme") === "dark";
      ctx.textBaseline = 'top';
      ctx.font = '10px sans-serif';
      ctx.fillStyle = isDark ? "#94a3b8" : "#64748b";
      ctx.textAlign = 'center';
      
      const yBaseline = chart.scales.y.getPixelForValue(0);
      
      chart.data.datasets.forEach(function(dataset, i) {
        const meta = chart.getDatasetMeta(i);
        if (!meta.hidden) {
            let lbl = "";
            if (dataset.label === "Budget") lbl = "Bgt";
            if (dataset.label === "Realisasi" || dataset.label === "Actual") lbl = "Act";
            if (!lbl) return;
            
            for (let j = 0; j < meta.data.length; j++) {
                if (meta.data[j]) {
                    ctx.fillText(lbl, meta.data[j].x, yBaseline + 10);
                }
            }
        }
      });
      ctx.restore();
    }
};

function setfRenderBudgetVsRealisasiChart(canvasId, labels, budgets, realisasis) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }
  
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#e2e8f0" : "#475569";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

  const budgetColors = labels.map(l => l === "TOTAL" ? (isDark ? "#475569" : "#cbd5e1") : setfColorForCategory(l) + "66");
  const realisasiColors = labels.map(l => l === "TOTAL" ? (isDark ? "#3b82f6" : "#3b82f6") : setfColorForCategory(l));

  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Budget",
          data: budgets,
          backgroundColor: budgetColors,
          borderRadius: 4,
          categoryPercentage: 0.8,
          barPercentage: 0.9
        },
        {
          label: "Realisasi",
          data: realisasis,
          backgroundColor: realisasiColors,
          borderRadius: 4,
          categoryPercentage: 0.8,
          barPercentage: 0.9
        }
      ]
    },
    plugins: [ChartDataLabels, setfTotalZonePlugin, setfGroupedSublabelPlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 35, bottom: 20 } },
      interaction: {
        mode: 'index',
        intersect: false,
      },
      onClick: function (evt, elements) {
        if (!elements.length) return;
        let lbl = labels[elements[0].index];
        if (lbl !== "TOTAL" && canvasId === "chart-kategori") {
            if (typeof setfSetKategoriDrilldown !== 'undefined') setfSetKategoriDrilldown(lbl);
        }
      },
      plugins: {
        legend: { position: "top", labels: { color: textColor } },
        datalabels: {
          display: true,
          align: 'end',
          anchor: 'end',
          color: textColor,
          font: { size: 10, weight: '500' },
          formatter: function(value) {
            return value ? setfFmtJutaan(value) : "";
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return context.dataset.label + ": " + setfFmtJutaan(context.raw);
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            callback: function(value) { return setfFmtJutaan(value); }
          }
        },
        x: {
          grid: { display: false },
          ticks: { 
            color: textColor,
            padding: 25 
          }
        }
      }
    }
  });
}
function setfRenderStackedGroupedChart(canvasId, years, dataList, mode) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#475569";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

    let activeItems = dataList;
    let rawDatasets = [];
    let showBudget = (mode === "all" || mode === "budget" || !mode);
    let showActual = (mode === "all" || mode === "actual" || mode === "realisasi" || !mode);

    const shapes = ['dot', 'diagonal-right-left', 'square', 'zigzag', 'triangle', 'weave', 'cross'];
    activeItems.forEach(function(item, idx) {
       let shape = shapes[idx % shapes.length];
       let color = setfColorForCategory(item.originalName || item.name);
       if (canvasId.includes("pillar")) {
           if (item.name === "AGRI") color = "#10b981";
           else if (item.name === "APP") color = "#3b82f6";
           else if (item.name === "FINANCE") color = "#f59e0b";
           else if (item.name === "SETF") color = "#8b5cf6";
           else color = "#64748b";
       }
       
       if (showBudget) {
           rawDatasets.push({
               label: item.name + " (Budget)",
               data: item.budget,
               backgroundColor: color,
               borderColor: setfShadeColor(color, -20),
               borderWidth: 1,
               stack: "StackBudget",
               barPercentage: 0.8,
               categoryPercentage: 0.8
           });
       }
       
       if (showActual) {
           rawDatasets.push({
               label: item.name + " (Actual)",
               data: item.realisasi,
               backgroundColor: typeof pattern !== 'undefined' ? pattern.draw(shape, color) : color,
               borderColor: setfShadeColor(color, -20),
               borderWidth: 1,
               stack: "StackRealisasi",
               barPercentage: 0.8,
               categoryPercentage: 0.8
           });
       }
    });

    let scalesCfg = {
        x: {
            stacked: true,
            ticks: { color: textColor, padding: 20 },
            grid: { color: gridColor, display: false }
        },
        y: {
            type: 'linear', display: true, position: 'left',
            stacked: true,
            ticks: { color: textColor, callback: function (value) { return setfFmtJutaan(value); } },
            grid: { color: gridColor }
        }
    };

    const dual = setfInjectDualYAxis(years, rawDatasets, scalesCfg);
    if (dual.scales['y-right']) dual.scales['y-right'].stacked = true;

    setfCharts[canvasId] = new Chart(ctx, {
        type: "bar",
        data: { labels: dual.labels, datasets: dual.datasets },
        plugins: [ChartDataLabels, setfStackTotalPlugin, setfTotalZonePlugin],
        options: {
            responsive: true,
            layout: { padding: { top: 20, bottom: 25 } },
            onClick: function (evt, elements) {
                if (!elements.length) return;
                const idx = elements[0].index;
                const clickedLabel = dual.labels[idx];
                if (clickedLabel !== "TOTAL" && canvasId === "chart-kategori") {
                    setfSetKategoriDrilldown(clickedLabel);
                }
            },
            plugins: {
                legend: { 
                   display: true,
                   position: 'top',
                   align: 'end',
                   labels: { 
                       color: textColor, boxWidth: 12,
                       generateLabels: function(chart) {
                           const original = Chart.defaults.plugins.legend.labels.generateLabels(chart);
                           let unique = [];
                           let seen = new Set();
                           original.forEach(function(item) {
                               if (item.text.includes('(Shadow)')) return;
                               const baseName = item.text.replace(" (Budget)", "").replace(" (Actual)", "");
                               if (!seen.has(baseName)) {
                                   seen.add(baseName);
                                   let newItem = Object.assign({}, item);
                                   newItem.text = baseName;
                                   newItem.datasetIndex = item.datasetIndex;
                                   unique.push(newItem);
                               }
                           });
                           return unique;
                       }
                   },
                   onClick: function(e, legendItem, legend) {
                       const index = legendItem.datasetIndex;
                       const ci = legend.chart;
                       const baseName = legendItem.text;
                       ci.data.datasets.forEach(function(ds, i) {
                           const dsBase = ds.label.replace(" (Budget)", "").replace(" (Actual)", "").replace(" (Shadow)", "");
                           if (dsBase === baseName) {
                               const meta = ci.getDatasetMeta(i);
                               meta.hidden = meta.hidden === null ? !ci.data.datasets[i].hidden : null;
                           }
                       });
                       ci.update();
                   }
                },
                datalabels: { display: false }
            },
            scales: dual.scales
        }
    });
}

function setfInjectDualYAxis(labels, rawDatasets, baseScales) {
    if (!labels || !labels.length) return { labels: [], datasets: rawDatasets, scales: baseScales };
    let newLabels = [...labels, "TOTAL"];
    let newDatasets = [];
    
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#475569";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";
    
    let totalBgt = 0;
    let totalAct = 0;
    
    rawDatasets.forEach(ds => {
        let newData = [...ds.data, 0]; 
        let shadowData = new Array(labels.length + 1).fill(0);
        
        if (ds.stack === "StackBudget") {
            const sum = ds.data.reduce((a, b) => a + (b||0), 0);
            shadowData[labels.length] = sum;
            totalBgt += sum;
        } else if (ds.stack === "StackRealisasi") {
            const sum = ds.data.reduce((a, b) => a + (b||0), 0);
            shadowData[labels.length] = sum;
            totalAct += sum;
        }
        
        ds.data = newData;
        ds.yAxisID = 'y';
        newDatasets.push(ds);
        
        let shadow = Object.assign({}, ds);
        shadow.data = shadowData;
        shadow.yAxisID = 'y-right';
        shadow.label = ds.label + " (Shadow)";
        shadow.backgroundColor = "transparent";
        shadow.borderColor = "transparent";
        if (typeof pattern !== 'undefined' && shadow.backgroundColor && shadow.backgroundColor.draw) {
            shadow.backgroundColor = "transparent"; 
        }
        newDatasets.push(shadow);
    });
    
    let yRight = {
        type: 'linear', display: true, position: 'right',
        stacked: true,
        ticks: { color: textColor, callback: function (value) { return setfFmtJutaan(value); } },
        grid: { drawOnChartArea: false, color: gridColor }
    };
    
    let maxLeft = Math.max(totalBgt, totalAct) * 1.1;
    baseScales['y'].max = maxLeft;
    yRight.max = maxLeft;
    
    baseScales['y-right'] = yRight;
    
    return { labels: newLabels, datasets: newDatasets, scales: baseScales };
}


function setfRenderFamilyTable(families) {
    const tbody = document.querySelector("#setf-family-table tbody");
    if (!tbody) return;
    if (!families || !families.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Belum ada data sahabat.</td></tr>';
      return;
    }
    tbody.innerHTML = families.map(function (f) {
      const memberRows = f.members.map(function (m) {
        const bgt = m.budget || 0;
        const sisa = bgt - m.realisasi;
        return "<tr><td>" + f.label + "</td><td>" + m.nama + "</td>" +
          "<td>" + setfCatBadgeList(m.kategori) + "</td>" +
          '<td class="num-right">' + setfFmtJutaan(bgt) + "</td>" +
          '<td class="num-right">' + setfFmtJutaan(m.realisasi) + "</td>" +
          setfSisaCell(sisa) + "</tr>";
      }).join("");
      
      const totalBudget = f.total_budget || f.members.reduce((a,b)=>a+(b.budget||0), 0);
      const totalSisa = totalBudget - f.total_realisasi;
      const totalRow = "<tr style=\"font-weight:bold\"><td>" + f.label + " - Total</td><td></td><td></td>" +
        '<td class="num-right">' + setfFmtJutaan(totalBudget) + "</td>" +
        '<td class="num-right">' + setfFmtJutaan(f.total_realisasi) + "</td>" +
        setfSisaCell(totalSisa) + "</tr>";
      return memberRows + totalRow;
    }).join("");
}


async function setfExportPdf() {
    showToast("Mempersiapkan PDF... Mohon tunggu.", "info");

    if (typeof html2pdf === 'undefined') {
        await new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    const container = document.createElement("div");
    container.style.position = "absolute";
    container.style.left = "-9999px";
    container.style.top = "-9999px";
    container.style.width = "1122px";
    container.style.background = "#ffffff";
    document.body.appendChild(container);

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#1e293b";
    const bgColor = isDark ? "#0f172a" : "#ffffff";
    const borderColor = isDark ? "#334155" : "#e2e8f0";

    const pairs = [
        { title: "Budget vs Actual per Kategori", chart: "chart-kategori", table: "setf-kategori-table" },
        { title: "Budget vs Actual per Pillar", chart: "chart-pillar", table: "setf-pillar-table" },
        { title: "Trend per Tahun per Kategori", chart: "chart-tahunan-kategori", table: "setf-tahunan-kategori-table" },
        { title: "Trend per Tahun per Pillar", chart: "chart-tahunan-pillar", table: "setf-tahunan-pillar-table" },
        { title: "Budget vs Actual per Sahabat", chart: "chart-keluarga", table: "setf-family-table" }
    ];

    pairs.forEach((pair, idx) => {
        const page = document.createElement("div");
        page.style.width = "1122px";
        page.style.height = "790px";
        page.style.padding = "40px";
        page.style.boxSizing = "border-box";
        page.style.display = "flex";
        page.style.flexDirection = "column";
        page.style.background = bgColor;
        page.style.color = textColor;
        
        if (idx < pairs.length - 1) {
            page.style.pageBreakAfter = "always";
        }

        const title = document.createElement("h2");
        title.innerText = pair.title;
        title.style.margin = "0 0 20px 0";
        title.style.fontFamily = "sans-serif";
        title.style.fontSize = "24px";
        page.appendChild(title);

        const content = document.createElement("div");
        content.style.display = "flex";
        content.style.flex = "1";
        content.style.gap = "20px";

        const chartSide = document.createElement("div");
        chartSide.style.flex = "0 0 73%";
        chartSide.style.display = "flex";
        chartSide.style.alignItems = "center";
        chartSide.style.justifyContent = "center";

        if (setfCharts[pair.chart]) {
            const chart = setfCharts[pair.chart];
            const parent = chart.canvas.parentNode;
            
            // Backup original state
            const origWidth = parent.style.width;
            const origHeight = parent.style.height;
            const origPos = parent.style.position;
            const origMaxWidth = parent.style.maxWidth;
            const origAspectRatio = chart.options.maintainAspectRatio;
            const origPixelRatio = chart.options.devicePixelRatio;
            const origAnimation = chart.options.animation;

            // Virtual layout configuration
            parent.style.position = "absolute";
            parent.style.maxWidth = "none";
            parent.style.width = "850px"; 
            parent.style.height = "500px";
            chart.options.maintainAspectRatio = false;
            chart.options.devicePixelRatio = 3; 
            chart.options.animation = false;
            
            // Apply layout changes SYNCHRONOUSLY
            chart.resize();
            chart.update('none');
            
            const img = document.createElement("img");
            img.src = chart.toBase64Image();
            
            // Restore original state
            parent.style.position = origPos;
            parent.style.maxWidth = origMaxWidth;
            parent.style.width = origWidth;
            parent.style.height = origHeight;
            chart.options.maintainAspectRatio = origAspectRatio !== undefined ? origAspectRatio : true;
            chart.options.devicePixelRatio = origPixelRatio || window.devicePixelRatio;
            chart.options.animation = origAnimation;
            
            // Apply original state SYNCHRONOUSLY
            chart.resize();
            chart.update('none');

            img.style.maxWidth = "100%";
            img.style.maxHeight = "100%";
            img.style.objectFit = "contain";
            chartSide.appendChild(img);
        }

        const tableSide = document.createElement("div");
        tableSide.style.flex = "0 0 25%";
        tableSide.style.overflow = "hidden";

        const originalTable = document.getElementById(pair.table);
        if (originalTable) {
            const tableClone = originalTable.cloneNode(true);
            tableClone.style.width = "100%";
            tableClone.style.borderCollapse = "collapse";
            tableClone.style.fontSize = "11px";
            tableClone.style.fontFamily = "sans-serif";
            
            const cells = tableClone.querySelectorAll("th, td");
            cells.forEach(cell => {
                cell.style.padding = "6px";
                cell.style.borderBottom = "1px solid " + borderColor;
                cell.style.color = textColor;
                if (cell.tagName === "TH") {
                    cell.style.textAlign = "left";
                    cell.style.fontWeight = "bold";
                    cell.style.background = isDark ? "#1e293b" : "#f8fafc";
                }
            });
            
            tableSide.appendChild(tableClone);
        }

        content.appendChild(chartSide);
        content.appendChild(tableSide);
        page.appendChild(content);
        container.appendChild(page);
    });

    const opt = {
        margin:       0,
        filename:     'Sahabat_ETF_Dashboard.pdf',
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, logging: false },
        jsPDF:        { unit: 'pt', format: 'a4', orientation: 'landscape' }
    };

    html2pdf().set(opt).from(container).save().then(() => {
        document.body.removeChild(container);
        showToast("PDF berhasil diunduh!", "success");
    }).catch(err => {
        console.error(err);
        document.body.removeChild(container);
        showToast("Terjadi kesalahan saat membuat PDF.", "error");
    });
}

// --- Diagram Pohon ---

function setfLoadPohon() {
  const years = Array.from(document.querySelectorAll('.setf-pohon-year-cb:checked')).map(cb => cb.value);
  const selMonth = document.getElementById('setf-pohon-month');
  
  const pillars = Array.from(document.querySelectorAll('.setf-pohon-pillar-cb:checked')).map(cb => cb.value);
  
  let qs = '';
  years.forEach(y => { qs += 'years[]=' + encodeURIComponent(y) + '&'; });
  qs = qs.slice(0, -1);

  if (selMonth) qs += '&month=' + encodeURIComponent(selMonth.value);
  pillars.forEach(p => { qs += '&pillars[]=' + encodeURIComponent(p); });

  const container1 = document.getElementById('setf-pohon-container');
  const container2 = document.getElementById('setf-pohon-group-container');
  
  if (container1) container1.innerHTML = '<div style="text-align:center;color:var(--text-muted)">Memuat data pohon...</div>';
  if (container2) container2.innerHTML = '';

  fetch('/beasiswa/sahabat/api/pohon?' + qs)
    .then(r => r.json())
    .then(resp => {
      if (!resp.ok) {
        showToast(resp.pesan || 'Gagal memuat diagram pohon.', 'error');
        return;
      }
      window._setfPohonLoaded = true;
      if (container1) container1.innerHTML = setfRenderDiagram1(resp.data.diagram1);
      if (container2) container2.innerHTML = setfRenderDiagram2(resp.data.diagram2);
    })
    .catch(e => {
      showToast('Gagal memuat diagram pohon.', 'error');
    });
}

function setfBuildTreeNode(nodeData, isGroupNode=false) {
  const widthClass = isGroupNode ? 'tree-node-group' : '';
  const label = nodeData.label || nodeData.group_name;
  
  let html = `
    <div class="tree-node ${widthClass}" style="margin: 0 auto;">
      <div class="tree-node-header">${label}</div>
      <div class="tree-node-body">
        <div class="tree-metrics">
          <div class="tree-metric-box">
            <div class="tree-metric-label">Plafon</div>
            <div class="tree-metric-val">${setfFmtJutaan(nodeData.plafon)}</div>
          </div>
          <div class="tree-metric-box">
            <div class="tree-metric-label">Realisasi</div>
            <div class="tree-metric-val">${setfFmtJutaan(nodeData.realisasi)}</div>
          </div>
        </div>
  `;
  
  const list = nodeData.siswa || nodeData.detail || [];
  if (list.length > 0) {
    html += `
        <div class="tree-table-wrap">
          <table class="tree-table">
            <thead>
              <tr>
                <th>Nama</th>
                <th style="text-align:right">Plafon</th>
                <th style="text-align:right">Realisasi</th>
              </tr>
            </thead>
            <tbody>
    `;
    let totPlafon = 0;
    let totRealisasi = 0;
    list.forEach(item => {
      totPlafon += item.plafon || 0;
      totRealisasi += item.realisasi || 0;
      html += `
              <tr>
                <td>${item.nama}</td>
                <td>${setfFmtJutaan(item.plafon)}</td>
                <td>${setfFmtJutaan(item.realisasi)}</td>
              </tr>
      `;
    });
    html += `
              <tr class="tree-total-row">
                <td>Total</td>
                <td>${setfFmtJutaan(totPlafon)}</td>
                <td>${setfFmtJutaan(totRealisasi)}</td>
              </tr>
            </tbody>
          </table>
        </div>
    `;
  }
  
  html += `
      </div>
    </div>
  `;
  return html;
}

function setfRenderDiagram1(data) {
  if (!data || !data.root) return '<div style="color:var(--text-muted)">Data kosong</div>';
  
  return `
    <style>
      .setf-tree-branch { display: flex; gap: 1.5rem; padding-top: 20px; position: relative; }
      .setf-tree-branch .tree-item { position: relative; display: flex; flex-direction: column; align-items: center; }
      .setf-tree-branch .tree-item::before { content:""; position:absolute; top: -20px; left: 50%; width: 2px; height: 20px; background: var(--accent); }
      .setf-tree-branch .tree-item::after { content:""; position:absolute; top: -20px; height: 2px; background: var(--accent); }
      .setf-tree-branch .tree-item:first-child::after { left: 50%; right: -0.75rem; }
      .setf-tree-branch .tree-item:last-child::after { right: 50%; left: -0.75rem; }
      .setf-tree-branch .tree-item:not(:first-child):not(:last-child)::after { left: -0.75rem; right: -0.75rem; }
      .setf-tree-branch .tree-item:first-child:last-child::after { display: none; }
      
      /* Print scale so the tree structure fits on A4 Landscape */
      @media print {
        #setf-pohon-group-container > div { zoom: 0.55; }
        #setf-pohon-container > div { zoom: 0.8; }
      }
    </style>
    <div style="display:flex; flex-direction:column; align-items:center; min-width: max-content; padding: 10px;">
      ${setfBuildTreeNode(data.root)}
      
      <div class="tree-connector-root" style="width: 2px; height: 20px; background: var(--accent);"></div>
      
      <div class="setf-tree-branch">
        <div class="tree-item">${setfBuildTreeNode(data.kesehatan)}</div>
        <div class="tree-item">${setfBuildTreeNode(data.pendidikan)}</div>
      </div>
    </div>
  `;
}

function setfRenderDiagram2(data) {
  if (!data || !data.root || !data.groups) return '';
  
  let groupsHtml = data.groups.map(g => `
    <div class="tree-item">
      ${setfBuildTreeNode(g, true)}
    </div>
  `).join('');
  
  return `
    <div style="display:flex; flex-direction:column; align-items:center; min-width: max-content; padding: 10px;">
      ${setfBuildTreeNode(data.root)}
      
      <div class="tree-connector-root" style="width: 2px; height: 20px; background: var(--accent);"></div>
      
      <div class="setf-tree-branch">
        ${groupsHtml}
      </div>
    </div>
  `;
}
