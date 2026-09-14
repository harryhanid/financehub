function setfHexToRgba(hex, alpha) {
    let r = parseInt(hex.slice(1, 3), 16),
        g = parseInt(hex.slice(3, 5), 16),
        b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// static/js/sahabat_etf.js
let setfCharts = {};

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
            if (dataset.label === "Actual") lbl = "Act";
            if (!lbl) return;
            
            for (let j = 0; j < meta.data.length; j++) {
                if (meta.data[j]) {
                    ctx.fillText(lbl, meta.data[j].x, yBaseline + 4);
                }
            }          }
        });
        
        // Draw main labels if they are arrays (to support bold first line)
        const xAxis = chart.scales.x;
        if (xAxis && xAxis.ticks) {
            xAxis.ticks.forEach(function(tick, idx) {
                const label = chart.data.labels[idx];
                if (Array.isArray(label) && label.length > 1) {
                    const xPos = xAxis.getPixelForTick(idx);
                    const yPos = yBaseline + 20;
                    
                    ctx.fillStyle = isDark ? "#e2e8f0" : "#475569";
                    ctx.font = 'bold 11px sans-serif';
                    ctx.fillText(label[0], xPos, yPos);
                    
                    ctx.font = '11px sans-serif';
                    ctx.fillText(label[1], xPos, yPos + 14);
                }
            });
        }
        
        ctx.restore();
      }
};

const SETF_BULAN_LABEL = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

const SETF_PALETTE = ["#6366f1", "#14b8a6", "#f97316", "#ec4899", "#10b981", "#f59e0b"];
const setfCategoryColorMap = {};
function setfColorForCategory(name) {
  if (!setfCategoryColorMap[name]) {
    const idx = Object.keys(setfCategoryColorMap).length % SETF_PALETTE.length;
    setfCategoryColorMap[name] = SETF_PALETTE[idx];
  }
  return setfCategoryColorMap[name];
}

function setfFmtJutaan(amount) {
  return fmtJutaan(amount);
}

function setfSisaCell(amount) {
  const cls = (amount || 0) < 0 ? ' class="setf-sisa-negative"' : "";
  return "<td" + cls + ">" + setfFmtJutaan(amount) + "</td>";
}

function setfMismatchCell(amount, mismatch) {
  const cls = mismatch ? ' class="setf-payment-mismatch"' : "";
  return "<td" + cls + ">" + setfFmtJutaan(amount) + "</td>";
}

function setfFirstName(fullName) {
  return (fullName || "").trim().split(/\s+/)[0] || "";
}

function setfColorScaleAttr(value, min, max) {
  if (!value) return "";
  const alpha = max > min ? 0.12 + ((value - min) / (max - min)) * 0.4 : 0.35;
  return ' style="background-color:rgba(99,102,241,' + alpha.toFixed(2) + ')"';
}

const SETF_CAT_BADGE_CLASS = {
  "By Pendidikan": "badge-cat-by-pendidikan",
  "By Tunjangan": "badge-cat-by-tunjangan",
  "By Penelitian": "badge-cat-by-penelitian",
  "By Medical": "badge-cat-by-medical",
};
function setfCatBadge(cat1) {
  if (!cat1) return "";
  const cls = SETF_CAT_BADGE_CLASS[cat1] || "badge-cat-lainnya";
  return '<span class="budget-badge ' + cls + '">' + cat1 + "</span>";
}
function setfCatBadgeList(kategoriCsv) {
  if (!kategoriCsv) return "";
  return kategoriCsv.split(",").map(function (c) { return setfCatBadge(c.trim()); }).join(" ");
}

const SETF_STATUS_BADGE_CLASS = {
  "Aktif": "badge-status-active",
  "lulus": "badge-status-completed",
  "gugur": "badge-status-expired",
  "undur diri": "badge-status-near-limit",
};
function setfStatusBadge(status) {
  if (!status) return "";
  const cls = SETF_STATUS_BADGE_CLASS[status] || "badge-status-active";
  return '<span class="budget-badge ' + cls + '">' + status + "</span>";
}

const SETF_JENJANG_BADGE_CLASS = {
  "SD": "setf-badge-jenjang-sd",
  "SMP": "setf-badge-jenjang-smp",
  "SMA": "setf-badge-jenjang-sma",
  "SMK": "setf-badge-jenjang-smk",
  "S1": "setf-badge-jenjang-s1",
  "S2": "setf-badge-jenjang-s2",
  "S3": "setf-badge-jenjang-s3",
  "SETF": "setf-badge-jenjang-setf",
};
function setfJenjangBadge(jenjang) {
  if (!jenjang) return "";
  const cls = SETF_JENJANG_BADGE_CLASS[jenjang] || "setf-badge-jenjang-lainnya";
  return '<span class="setf-badge-jenjang ' + cls + '">' + jenjang + "</span>";
}

function setfThemeColor(varName, fallback) {
  const page = document.querySelector(".budget-page");
  const val = page ? getComputedStyle(page).getPropertyValue(varName).trim() : "";
  return val || fallback;
}

function setfShadeColor(hex, percent) {
  const num = parseInt(hex.replace("#", ""), 16);
  const amt = Math.round(2.55 * percent);
  let r = (num >> 16) + amt;
  let g = ((num >> 8) & 0x00ff) + amt;
  let b = (num & 0x0000ff) + amt;
  r = Math.min(255, Math.max(0, r));
  g = Math.min(255, Math.max(0, g));
  b = Math.min(255, Math.max(0, b));
  return "#" + (0x1000000 + r * 0x10000 + g * 0x100 + b).toString(16).slice(1);
}

function setfDatalabelFormatter(value) {
  return value ? setfFmtJutaan(value) : null;
}

function setfRenderBarChart(canvasId, labels, datasets, onBarClick) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }
  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    plugins: [ChartDataLabels, setfGroupedSublabelPlugin],
    options: {
      responsive: true,
      onClick: function (evt, elements) {
        if (!elements.length || !onBarClick) return;
        onBarClick(elements[0].index);
      },
      plugins: {
        legend: { labels: { color: setfThemeColor("--text-primary", "#e2e8f0") } },
        datalabels: {
          anchor: "end",
          align: "top",
          color: setfThemeColor("--text-primary", "#e2e8f0"),
          font: { size: 10, weight: "600" },
          formatter: setfDatalabelFormatter,
        },
      },
      scales: {
        x: { 
            ticks: {
              color: setfThemeColor("--text-secondary", "#94a3b8"),
              callback: function(val, idx) {
                  let lbl = this.getLabelForValue(val);
                  if (Array.isArray(lbl)) return lbl.map(function(x) { return "               "; });
                  return lbl;
              }
            }, 
            grid: { color: "rgba(148,163,184,0.1)" } 
          },
        y: {
          ticks: {
            color: setfThemeColor("--text-secondary", "#94a3b8"),
            callback: function (value) { return setfFmtJutaan(value); },
          },
          grid: { color: "rgba(148,163,184,0.1)" },
        },
      },
    },
  });
}


  function setfRenderStackedBarChart(canvasId, families) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#e2e8f0" : "#475569";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

  const maxMembers = families.reduce(function (m, f) { return Math.max(m, f.members.length); }, 0);
  const datasets = [];
  const shapes = ['dot', 'diagonal-right-left', 'square', 'zigzag', 'triangle', 'weave', 'cross'];
  
  for (let i = 0; i < maxMembers; i++) {
    const color = SETF_PALETTE[i % SETF_PALETTE.length];
    const shape = shapes[i % shapes.length];
    datasets.push({
      label: "Anggota " + (i + 1) + " (Budget)",
      data: families.map(function (f) { return i < f.members.length ? f.members[i].budget : null; }),
      backgroundColor: color,
      borderColor: setfShadeColor(color, -20),
      borderWidth: 1,
      stack: "StackBudget",
      barPercentage: 0.8,
      categoryPercentage: 0.8
    });
    datasets.push({
      label: "Anggota " + (i + 1) + " (Actual)",
      data: families.map(function (f) { return i < f.members.length ? f.members[i].realisasi : null; }),
      backgroundColor: typeof pattern !== 'undefined' ? pattern.draw(shape, color) : color,
      borderColor: setfShadeColor(color, -20),
      borderWidth: 1,
      stack: "StackRealisasi",
      barPercentage: 0.8,
      categoryPercentage: 0.8
    });
  }

  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: families.map(function (f) { return f.label; }), datasets: datasets },
    plugins: [ChartDataLabels, setfStackTotalPlugin],
    options: {
      responsive: true,
      layout: { padding: { top: 20, bottom: 25 } },
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
          display: false
        }
      },
      scales: {
        x: { 
            stacked: true, 
            ticks: { color: isDark ? "#94a3b8" : "#64748b", padding: 20 }, 
            grid: { color: isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)", display: false } 
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
    }
  });
}

function setfRenderDoughnutChart(canvasId, labels, values, colors) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }
  setfCharts[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors }] },
    plugins: [ChartDataLabels, setfGroupedSublabelPlugin],
    options: {
      responsive: true,
      onClick: function (evt, elements) {
        if (!elements.length) return;
        setfSetKategoriDrilldown(labels[elements[0].index]);
      },
      plugins: {
        legend: { position: "right", labels: { color: setfThemeColor("--text-primary", "#e2e8f0") } },
        datalabels: {
          anchor: "center",
          align: "center",
          color: "#fff",
          font: { size: 10, weight: "600" },
          formatter: setfDatalabelFormatter,
        },
      },
    },
  });
}

function setfRenderSummaryCards(rows) {
  const totalSiswa = rows.filter(function (r) { return r.status === "Aktif"; }).length;
  const totalBudget = rows.reduce(function (s, r) { return s + r.budget_total; }, 0);
  const totalPayment = rows.reduce(function (s, r) { return s + r.payment_total; }, 0);
  const totalRealisasi = rows.reduce(function (s, r) { return s + r.realisasi_total; }, 0);
  const totalSisa = rows.reduce(function (s, r) { return s + r.sisa_budget; }, 0);
  const cards = [
    ["Total Anggota Aktif", totalSiswa, ""],
    ["Total Budget", setfFmtJutaan(totalBudget), ""],
    ["Total Klaim", setfFmtJutaan(totalPayment), ""],
    ["Total Realisasi", setfFmtJutaan(totalRealisasi), " setf-stat-realisasi"],
    ["Sisa Budget", setfFmtJutaan(totalSisa), totalSisa < 0 ? " setf-sisa-negative" : ""],
  ];
  document.getElementById("setf-summary").innerHTML = cards.map(function (c) {
    return '<div class="budget-stat-card' + c[2] + '"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
  }).join("");
}

function setfRenderSummarySkeleton() {
  document.getElementById("setf-summary").innerHTML = Array(5).fill(0).map(function () {
    return '<div class="budget-stat-card"><div class="label">&nbsp;</div>' +
      '<div class="fh-skel" style="width:70%;height:20px;margin-top:.25rem"></div></div>';
  }).join("");
}

function setfRenderTable(rows) {
  const tbody = document.querySelector("#setf-table tbody");
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted)">Belum ada anggota Sahabat ETF.</td></tr>';
    return;
  }
  const rowsHtml = rows.map(function (r) {
    const mismatch = Math.round(r.payment_total) !== Math.round(r.realisasi_total);
    return "<tr>" +
      "<td>" + r.nama + "</td>" +
      "<td>" + setfJenjangBadge(r.jenjang) + "</td>" +
      "<td>" + r.angkatan + "</td>" +
      "<td>" + setfStatusBadge(r.status) + "</td>" +
      "<td>" + setfFmtJutaan(r.budget_total) + "</td>" +
      setfMismatchCell(r.payment_total, mismatch) +
      setfMismatchCell(r.realisasi_total, mismatch) +
      setfSisaCell(r.sisa_budget) +
      "</tr>";
  }).join("");
  const totalBudget = rows.reduce(function (s, r) { return s + r.budget_total; }, 0);
  const totalPayment = rows.reduce(function (s, r) { return s + r.payment_total; }, 0);
  const totalRealisasi = rows.reduce(function (s, r) { return s + r.realisasi_total; }, 0);
  const totalSisa = rows.reduce(function (s, r) { return s + r.sisa_budget; }, 0);
  const totalMismatch = Math.round(totalPayment) !== Math.round(totalRealisasi);
  const totalRow = "<tr style=\"font-weight:bold\"><td>Total</td><td></td><td></td><td></td>" +
    "<td>" + setfFmtJutaan(totalBudget) + "</td>" +
    setfMismatchCell(totalPayment, totalMismatch) +
    setfMismatchCell(totalRealisasi, totalMismatch) +
    setfSisaCell(totalBudget - totalRealisasi) + "</tr>";
  tbody.innerHTML = rowsHtml + totalRow;
}

function setfRenderKategoriTable(kategoriRows) {
  const tbody = document.querySelector("#setf-kategori-table tbody");
  if (!kategoriRows.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Belum ada data kategori.</td></tr>';
    return;
  }
  
  let html = "";
  
  // PENDIDIKAN
  let penBgt = 0, penAct = 0;
  let tunjangan = kategoriRows.find(k => k.cat1 === "By Tunjangan");
    let pendidikan = kategoriRows.find(k => k.cat1 === "By Pendidikan");
    let penelitian = kategoriRows.find(k => k.cat1 === "By Penelitian");
    
    if (tunjangan || pendidikan || penelitian) {
      html += "<tr style='background:transparent;'><td colspan='4'><strong style='font-size:1.05em;'>Pendidikan</strong></td></tr>";
      
      if (tunjangan) {
          penBgt += tunjangan.budget;
          penAct += tunjangan.realisasi;
          html += "<tr><td>" + setfCatBadge(tunjangan.cat1) + "</td><td>" + setfFmtJutaan(tunjangan.budget) + "</td><td>" + setfFmtJutaan(tunjangan.realisasi) + "</td>" + setfSisaCell(tunjangan.budget - tunjangan.realisasi) + "</tr>";
      }
      if (pendidikan) {
            penBgt += pendidikan.budget;
            penAct += pendidikan.realisasi;
            html += "<tr><td>" + setfCatBadge(pendidikan.cat1) + "</td><td>" + setfFmtJutaan(pendidikan.budget) + "</td><td>" + setfFmtJutaan(pendidikan.realisasi) + "</td>" + setfSisaCell(pendidikan.budget - pendidikan.realisasi) + "</tr>";
        }
        if (penelitian) {
            penBgt += penelitian.budget;
            penAct += penelitian.realisasi;
            html += "<tr><td>" + setfCatBadge(penelitian.cat1) + "</td><td>" + setfFmtJutaan(penelitian.budget) + "</td><td>" + setfFmtJutaan(penelitian.realisasi) + "</td>" + setfSisaCell(penelitian.budget - penelitian.realisasi) + "</tr>";
        }
      
      html += "<tr style='background:rgba(0,0,0,0.03); font-weight:bold;'><td>Sub Total Pendidikan</td><td>" + setfFmtJutaan(penBgt) + "</td><td>" + setfFmtJutaan(penAct) + "</td>" + setfSisaCell(penBgt - penAct) + "</tr>";
  }
  
  // KESEHATAN
  let medBgt = 0, medAct = 0;
  let medical = kategoriRows.find(k => k.cat1 === "By Medical");
  if (medical) {
      medBgt += medical.budget;
      medAct += medical.realisasi;
      html += "<tr style='background:transparent;'><td colspan='4'><strong style='font-size:1.05em;'>Kesehatan</strong></td></tr>";
      html += "<tr><td>" + setfCatBadge(medical.cat1) + "</td><td>" + setfFmtJutaan(medical.budget) + "</td><td>" + setfFmtJutaan(medical.realisasi) + "</td>" + setfSisaCell(medical.budget - medical.realisasi) + "</tr>";
      html += "<tr style='background:rgba(0,0,0,0.03); font-weight:bold;'><td>Sub Total Kesehatan</td><td>" + setfFmtJutaan(medBgt) + "</td><td>" + setfFmtJutaan(medAct) + "</td>" + setfSisaCell(medBgt - medAct) + "</tr>";
  }
  
  const totalBudget = kategoriRows.reduce((s, k) => s + k.budget, 0);
  const totalRealisasi = kategoriRows.reduce((s, k) => s + k.realisasi, 0);
  const totalRow = "<tr style='font-weight:bold; background:var(--bg-secondary)'><td>Total Pendidikan dan Kesehatan</td>" +
    "<td>" + setfFmtJutaan(totalBudget) + "</td>" +
    "<td>" + setfFmtJutaan(totalRealisasi) + "</td>" +
    setfSisaCell(totalBudget - totalRealisasi) + "</tr>";
    
  tbody.innerHTML = html + totalRow;
}

function setfRenderExecSummary(data) {
  const card = document.getElementById("setf-exec-summary-card");
  const textEl = document.getElementById("setf-exec-summary-text");
  if (!card || !textEl) return;
  card.style.display = "block";

  const kategori = data.kategori || [];
  const pillar = data.pillar || [];

  let totalBgt = 0, totalAct = 0;
  let penAct = 0, kesAct = 0;

  kategori.forEach(k => {
    totalBgt += k.budget || 0;
    totalAct += k.realisasi || 0;
    if (["By Pendidikan", "By Tunjangan", "By Penelitian"].includes(k.cat1)) {
      penAct += k.realisasi || 0;
    } else if (k.cat1 === "By Medical") {
      kesAct += k.realisasi || 0;
    }
  });

  let setfAct = 0, nonSetfAct = 0;
  pillar.forEach(p => {
    if (p.pillar === "SETF") {
      setfAct += p.realisasi || 0;
    } else {
      nonSetfAct += p.realisasi || 0;
    }
  });

  // Calculate percentages
  const pctTotal = totalBgt > 0 ? (totalAct / totalBgt * 100).toFixed(1) : "0.0";
  const pctPen = totalAct > 0 ? (penAct / totalAct * 100).toFixed(1) : "0.0";
  const pctKes = totalAct > 0 ? (kesAct / totalAct * 100).toFixed(1) : "0.0";
  const pctSetf = totalAct > 0 ? (setfAct / totalAct * 100).toFixed(1) : "0.0";
  const pctNonSetf = totalAct > 0 ? (nonSetfAct / totalAct * 100).toFixed(1) : "0.0";

  // Date formatting
  const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agt", "Sept", "Okt", "Nov", "Des"];
  const today = new Date();
  const dateStr = today.getDate() + " " + months[today.getMonth()] + " " + today.getFullYear();

  const summary = `Total Budget sebesar <strong>Rp ${setfFmtJutaan(totalBgt)}</strong> dengan realisasi sampai dengan ${dateStr} mencapai <strong>${pctTotal}%</strong> dengan rincian Pendidikan (By Pendidikan + By Tunjangan + By Penelitian) sebesar Rp ${setfFmtJutaan(penAct)} (${pctPen}%) dan Kesehatan (By Medical) sebesar Rp ${setfFmtJutaan(kesAct)} (${pctKes}%). <br><br>Porsi Beasiswa yang ditanggung SETF sebesar Rp ${setfFmtJutaan(setfAct)} atau ${pctSetf}% dan Non SETF (AGRI, APP, FINANCE) sebesar Rp ${setfFmtJutaan(nonSetfAct)} atau ${pctNonSetf}% dari Total Realisasi <strong>Rp ${setfFmtJutaan(totalAct)}</strong>.`;

  textEl.innerHTML = summary;
}

function setfRenderMonthlyChart(months) {
  setfRenderBarChart("chart-bulanan", months.map(function (m) { return SETF_BULAN_LABEL[m.bulan - 1]; }), [
    { label: "Actual", data: months.map(function (m) { return m.realisasi; }), backgroundColor: "#818cf8" },
  ], setfHighlightMonthlyRow);
}

function setfRenderMonthlyTable(comparison, years) {
  const theadRow = document.getElementById("setf-monthly-thead-row");
  theadRow.innerHTML = "<th>Bulan</th>" + years.map(function (y) { return "<th>" + y + "</th>"; }).join("");

  const tbody = document.querySelector("#setf-monthly-table tbody");
  if (!comparison.length) {
    tbody.innerHTML = '<tr><td colspan="' + (years.length + 1) + '" style="text-align:center;color:var(--text-muted)">Pilih minimal 1 tahun.</td></tr>';
    return;
  }
  const allValues = [];
  comparison.forEach(function (row) {
    years.forEach(function (y) {
      const v = row.per_tahun[y] || 0;
      if (v > 0) allValues.push(v);
    });
  });
  const minVal = allValues.length ? Math.min.apply(null, allValues) : 0;
  const maxVal = allValues.length ? Math.max.apply(null, allValues) : 0;

  const rows = comparison.map(function (row) {
    const cells = years.map(function (y) {
      const v = row.per_tahun[y] || 0;
      return "<td" + setfColorScaleAttr(v, minVal, maxVal) + ">" + setfFmtJutaan(v) + "</td>";
    }).join("");
    return "<tr><td>" + SETF_BULAN_LABEL[row.bulan - 1] + "</td>" + cells + "</tr>";
  }).join("");
  const totalCells = years.map(function (y) {
    const total = comparison.reduce(function (s, row) { return s + (row.per_tahun[y] || 0); }, 0);
    return "<td>" + setfFmtJutaan(total) + "</td>";
  }).join("");
  const totalRow = "<tr style=\"font-weight:bold\"><td>Total</td>" + totalCells + "</tr>";
  tbody.innerHTML = rows + totalRow;
}


function setfRenderTotalTable(tableId, dataList) {
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

function setfRenderTotalTable(tableId, dataList, years) {
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
       if (item.isSubTotal || item.isHeaderOnly) return;
       item.realisasi.forEach(function(val, idx) {
           if ((val || 0) > maxPerYear[idx]) maxPerYear[idx] = val;
       });
    });
    
    dataList.forEach(function(item) {
       const totalRealisasi = item.realisasi.reduce((a, b) => a + (b||0), 0);
       
       if (!item.isSubTotal && !item.isHeaderOnly) grandRealisasi += totalRealisasi;
       
       let nameHtml = item.name;
       let trStyle = "";
       if (item.isHeaderOnly) {
           nameHtml = "<strong style='font-size:1.05em;'>" + item.name + "</strong>";
       } else if (item.isSubTotal) {
           nameHtml = "<strong>" + item.name + "</strong>";
           trStyle = " style='background:rgba(0,0,0,0.03);'";
       } else {
           if (tableId.includes("kategori")) nameHtml = setfCatBadge(item.name);
           else if (tableId.includes("pillar")) nameHtml = setfPillarBadge(item.name);
       }
       
       let rowHtml = "<tr" + trStyle + "><td>" + nameHtml + "</td>";
       
       item.realisasi.forEach(function(val, idx) {
           if (item.isHeaderOnly) {
               rowHtml += "<td class='num-right'></td>";
               return;
           }
           if (!item.isSubTotal) grandYearlyRealisasi[idx] += (val || 0);
           let v = val || 0;
           let tdStyle = "";
           if (!item.isSubTotal && v > 0 && v === maxPerYear[idx]) {
               tdStyle = " style='font-weight:bold; color:var(--positive, #10b981); background:rgba(16, 185, 129, 0.1); border-radius: 4px;'";
           }
           let innerHtml = setfFmtJutaan(v);
           if (item.isSubTotal) innerHtml = "<strong>" + innerHtml + "</strong>";
           rowHtml += "<td class='num-right'" + tdStyle + ">" + innerHtml + "</td>";
       });
       if (item.isHeaderOnly) {
           rowHtml += "<td class='num-right'></td></tr>";
       } else {
           rowHtml += "<td class='num-right' style='font-weight:bold;'>" + setfFmtJutaan(totalRealisasi) + "</td></tr>";
       }
       tbodyHtml += rowHtml;
    });
    
    let grandTotalLabel = tableId.includes("kategori") ? "Total Pendidikan dan Kesehatan" : "Total Keseluruhan";
    let totalRowHtml = "<tr style='font-weight:bold; background:var(--bg-secondary)'><td>" + grandTotalLabel + "</td>";
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
}

function setfRenderPillarTable(pillarRows) {
  const tbody = document.querySelector("#setf-pillar-table tbody");
  if (!pillarRows.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data pillar.</td></tr>';
    return;
  }
  const rows = pillarRows.map(function (p) {
    return "<tr>" +
      "<td>" + setfPillarBadge(p.pillar) + "</td>" +
      "<td>" + setfFmtJutaan(p.budget) + "</td>" +
      "<td>" + setfFmtJutaan(p.realisasi) + "</td>" +
      setfSisaCell(p.sisa) +
      "</tr>";
  }).join("");
  const totalBudget = pillarRows.reduce(function (s, p) { return s + p.budget; }, 0);
  const totalRealisasi = pillarRows.reduce(function (s, p) { return s + p.realisasi; }, 0);
  
  const totalRow = "<tr style=\"font-weight:bold\"><td>Total</td>" +
    "<td>" + setfFmtJutaan(totalBudget) + "</td>" +
    "<td>" + setfFmtJutaan(totalRealisasi) + "</td>" +
    setfSisaCell(totalBudget - totalRealisasi) + "</tr>";
  tbody.innerHTML = rows + totalRow;
}

function setfRenderLatestPaymentsTable(rows) {
  const tbody = document.querySelector("#setf-latest-payments-table tbody");
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Belum ada transaksi.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(function (r) {
    return "<tr>" +
      "<td>" + r.tanggal + "</td>" +
      "<td>" + r.nama + "</td>" +
      "<td>" + setfCatBadge(r.cat1) + "</td>" +
      "<td>" + (r.cat2 || "") + "</td>" +
      '<td class="num-right">' + setfFmtJutaan(r.amount) + "</td>" +
      "</tr>";
  }).join("");
}

function setfGetSelectedFilters() {
  const years = Array.from(document.querySelectorAll(".setf-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillars = Array.from(document.querySelectorAll(".setf-pillar-cb:checked")).map(function (cb) { return cb.value; });
  return { years: years, pillars: pillars };
}

function setfBuildQueryString(filters) {
  const params = new URLSearchParams();
  if (filters.years.length) params.set("years", filters.years.join(","));
  if (filters.pillars.length) params.set("pillars", filters.pillars.join(","));
  return params.toString();
}

function setfUpdateExportLinks(qs) {
  const summaryLink = document.getElementById("setf-export-summary");
  const baseSummary = summaryLink.href.split("?")[0];
  summaryLink.href = qs ? baseSummary + "?" + qs : baseSummary;
}

function setfUpdateReportExportLink() {
  const sel = document.getElementById("setf-report-year");
  const link = document.getElementById("setf-export-report");
  if (!sel || !link) return;
  link.href = "/beasiswa/sahabat/export/report?year=" + encodeURIComponent(sel.value);
}



function setfApplyFilters() {
  const filters = setfGetSelectedFilters();
  const qs = setfBuildQueryString(filters);
  setfUpdateExportLinks(qs);

  setfActiveKategoriDrilldown = null;
  setfRenderDrilldownChip();

  setfRenderSummarySkeleton();
  document.querySelector("#setf-table tbody").innerHTML = skeletonRows(8, 6);
  document.querySelector("#setf-kategori-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-latest-payments-table tbody").innerHTML = skeletonRows(5, 6);
  document.querySelector("#setf-pillar-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-family-table tbody").innerHTML = skeletonRows(4, 6);

  setfRefetchLatestPayments();

  fetch("/beasiswa/sahabat/api/family_summary" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
        window._setfLastKeluargaData = data.families;
        setfRenderKeluargaChart(data.families);
        setfRenderFamilyTable(data.families);
    })
    .catch(function () { showToast("Gagal memuat data sahabat.", "error"); });

  fetch("/beasiswa/sahabat/api/summary" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfRenderSummaryCards(data.rows);
      setfRenderTable(data.rows);
    })
    .catch(function () { showToast("Gagal memuat ringkasan anggota.", "error"); });

  fetch("/beasiswa/sahabat/api/breakdown" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      let catLabels = data.kategori.map(function (k) { return k.cat1 || "Tanpa Kategori"; });
      let catBudgets = data.kategori.map(function (k) { return k.budget; });
      let catRealisasis = data.kategori.map(function (k) { return k.realisasi; });
      setfRenderBudgetVsRealisasiChart("chart-kategori", catLabels, catBudgets, catRealisasis);
      
      let pillarLabels = data.pillar.map(function(p) { return p.pillar; });
      let pillarBudgets = data.pillar.map(function(p) { return p.budget; });
      let pillarRealisasis = data.pillar.map(function(p) { return p.realisasi; });
      setfRenderBudgetVsRealisasiChart("chart-pillar", pillarLabels, pillarBudgets, pillarRealisasis);
      setfRenderKategoriTable(data.kategori);
      setfRenderExecSummary(data);
      setfRenderYearlyChart(data.yearly);
      setfRenderPillarTable(data.pillar);
    })
    .catch(function () { showToast("Gagal memuat breakdown kategori.", "error"); });

  if (filters.years.length) {
    document.querySelector("#setf-monthly-table tbody").innerHTML = skeletonRows(2, 4);
    fetch("/beasiswa/sahabat/api/monthly?" + qs)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        setfRenderMonthlyChart(data.months);
        setfRenderMonthlyTable(data.comparison, filters.years);
      })
      .catch(function () { showToast("Gagal memuat data bulanan.", "error"); });
  } else {
    if (setfCharts["chart-bulanan"]) { setfCharts["chart-bulanan"].destroy(); delete setfCharts["chart-bulanan"]; }
    setfRenderMonthlyTable([], []);
  }
}

function initSetfSubtabs() {
  const buttons = document.querySelectorAll(".setf-subtab-btn");
  const panels = document.querySelectorAll(".setf-subtab-panel");
  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      buttons.forEach(function (b) { b.classList.remove("active"); });
      panels.forEach(function (p) { p.classList.remove("active"); });
      btn.classList.add("active");
      const panel = document.getElementById("setf-subtab-" + btn.dataset.subtab);
      if (panel) panel.classList.add("active");
      if (btn.dataset.subtab === "laporan" && !window._setfLaporanLoaded) {
        window._setfLaporanLoaded = true;
        setfLoadLaporan();
      }
      if (btn.dataset.subtab === "detail" && !window._setfDetailLoaded) {
          window._setfDetailLoaded = true;
          setfLoadDetailTransaksi();
        }
        if (btn.dataset.subtab === "pohon" && !window._setfPohonLoaded) {
          window._setfPohonLoaded = true;
          setfLoadPohon();
        }
    });
  });
}

function initSahabatEtf() {
    if (typeof pattern === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/patternomaly@1.3.2/dist/patternomaly.min.js';
        script.onload = function() {
            setfApplyFilters();
        };
        document.head.appendChild(script);
        // Don't render immediately, wait for patternomaly
        return;
    }

  // Hanya inisialisasi satu kali — dipanggil dari onclick tombol tab
  // "Sahabat ETF" di Beasiswa setiap kali tab diklik, tidak hanya sekali
  // seperti DOMContentLoaded pada halaman standalone-nya.
  if (window._sahabatInitialized) return;
  window._sahabatInitialized = true;

  initSetfSubtabs();
  // Scoped to each sub-tab's own container — Dashboard and Detail Transaksi
  // each have their own .beasiswa-dash-filter-chip instances (different
  // checkbox classes), so a document-wide call would wire both sets to the
  // same callback.
  initFilterChips(document.getElementById("setf-subtab-dashboard"), setfApplyFilters);
  initFilterChips(document.getElementById("setf-subtab-detail"), setfLoadDetailTransaksi);
    initFilterChips(document.getElementById("setf-subtab-pohon"), setfLoadPohon);
    
    
  const reportYearSelect = document.getElementById("setf-report-year");
  if (reportYearSelect) {
    reportYearSelect.addEventListener("change", setfUpdateReportExportLink);
    reportYearSelect.addEventListener("change", function () {
      if (window._setfLaporanLoaded) setfLoadLaporan();
    });
    setfUpdateReportExportLink();
  }
  setfApplyFilters();
}

window.addEventListener("fh-theme-changed", function () {
  if (setfCharts["chart-kategori"] || setfCharts["chart-bulanan"] || setfCharts["chart-tahunan"] || setfCharts["chart-keluarga"]) {
    setfApplyFilters();
  }
});

// ─── Laporan tab: on-screen rendering of the Excel report's data ────────────
function setfLaporanHeaderRow(reportYear) {
  return '<tr class="setf-laporan-header">' +
    '<th rowspan="2">Nama</th><th rowspan="2">Periode</th><th rowspan="2">Pillar</th>' +
    '<th colspan="5">Tahun ' + reportYear + '</th>' +
    '<th colspan="5">S/D Tahun ' + reportYear + '</th></tr>' +
    '<tr class="setf-laporan-header">' +
    '<th>Plafon</th><th>PTA</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th>' +
    '<th>Plafon</th><th>PTA</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th></tr>';
}

function setfLaporanMetricsCells(m) {
  return '<td class="num-right">' + setfFmtJutaan(m.cur.plafon) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cur.pta) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cur.klaim) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cur.dibayar) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cur.saldo) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cum.plafon) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cum.pta) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cum.klaim) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cum.dibayar) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cum.saldo) + '</td>';
}

function setfLaporanPeriodeText(row) {
  if (!row.periode_start || !row.periode_end) return '';
  return row.periode_start + ' - ' + row.periode_end;
}

function setfLaporanNamaRow(row, cls) {
  return '<tr class="' + cls + '"><td>' + row.nama + '</td><td>' + setfLaporanPeriodeText(row) + '</td><td>' + row.pillar + '</td>' +
    setfLaporanMetricsCells(row) + '</tr>';
}

function setfLaporanLabelRow(label, metrics, cls) {
  return '<tr class="' + cls + '"><td colspan="3">' + label + '</td>' +
    setfLaporanMetricsCells(metrics) + '</tr>';
}

function setfRenderLaporanSection(section, reportYear) {
  let html = '<h4 class="setf-laporan-section-title">' + section.label + '</h4>';
  html += '<table class="setf-laporan-table"><thead>' + setfLaporanHeaderRow(reportYear) + '</thead><tbody>';
  section.groups.forEach(function (group) {
    html += setfLaporanLabelRow(group.label, group.subtotal, 'setf-laporan-subtotal-row');
    group.siswa_rows.forEach(function (row) {
      html += setfLaporanNamaRow(row, 'setf-laporan-siswa-row');
    });
  });
  html += setfLaporanLabelRow('TOTAL ' + section.label, section.total, 'setf-laporan-total-row');
  html += '</tbody></table>';
  if (section.recap.length) {
    html += '<table class="setf-laporan-table setf-laporan-recap">' +
      '<caption>Rekap ' + section.label + '</caption><thead>' + setfLaporanHeaderRow(reportYear) + '</thead><tbody>';
    section.recap.forEach(function (row) {
      html += setfLaporanNamaRow(row, 'setf-laporan-recap-row');
    });
    html += '</tbody></table>';
  }
  return html;
}

function setfRenderLaporanPillarBreakdown(pillarBreakdown, grandTotal, reportYear) {
  let html = '<h4 class="setf-laporan-section-title">Breakdown Pillar</h4>';
  html += '<table class="setf-laporan-table"><thead>' + setfLaporanHeaderRow(reportYear) + '</thead><tbody>';
  html += setfLaporanLabelRow('GRAND TOTAL', grandTotal, 'setf-laporan-total-row');
  pillarBreakdown.forEach(function (p) {
    html += '<tr class="setf-laporan-subtotal-row"><td colspan="3">' + setfPillarBadge(p.pillar_label) + '</td>' +
      setfLaporanMetricsCells(p) + '</tr>';
    html += '<tr class="setf-laporan-pct-row"><td colspan="3">% to total</td>' +
      '<td class="num-right">' + (p.pct_cur.plafon * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cur.pta * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cur.klaim * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cur.dibayar * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cur.saldo * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cum.plafon * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cum.pta * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cum.klaim * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cum.dibayar * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cum.saldo * 100).toFixed(1) + '%</td></tr>';
  });
  html += '</tbody></table>';
  return html;
}

function setfRenderLaporan(data) {
  let html = '<h3>REPORT — Tahun ' + data.report_year + '</h3>';
  data.sections.forEach(function (section) {
    html += setfRenderLaporanSection(section, data.report_year);
  });
  html += '<h4 class="setf-laporan-section-title">Total Pendidikan &amp; Kesehatan</h4>';
  html += '<table class="setf-laporan-table"><thead>' + setfLaporanHeaderRow(data.report_year) + '</thead><tbody>';
  html += setfLaporanLabelRow('TOTAL PENDIDIKAN &amp; KESEHATAN', data.combined_total, 'setf-laporan-total-row');
  data.combined_recap.forEach(function (row) {
    html += setfLaporanNamaRow(row, 'setf-laporan-recap-row');
  });
  html += setfLaporanLabelRow('GRAND TOTAL', data.grand_total, 'setf-laporan-total-row');
  html += '</tbody></table>';
  html += setfRenderLaporanPillarBreakdown(data.pillar_breakdown, data.grand_total, data.report_year);
  document.getElementById('setf-laporan-content').innerHTML = html;
}

function setfLoadLaporan() {
  const sel = document.getElementById('setf-report-year');
  if (!sel) return;
  document.getElementById('setf-laporan-content').innerHTML =
    '<p style="color:var(--text-muted);text-align:center;padding:2rem">Memuat laporan...</p>';
  fetch('/beasiswa/sahabat/api/report?year=' + encodeURIComponent(sel.value))
    .then(function (r) { return r.json(); })
    .then(function (resp) {
      if (!resp.ok) { showToast(resp.pesan || 'Gagal memuat laporan.', 'error'); return; }
      setfRenderLaporan(resp.data);
    })
    .catch(function () { showToast('Gagal memuat laporan.', 'error'); });
}

// ─── Detail Transaksi tab: full transaction list ────────────────────────────
function setfGetDetailFilters() {
  const years = Array.from(document.querySelectorAll(".setf-detail-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillars = Array.from(document.querySelectorAll(".setf-detail-pillar-cb:checked")).map(function (cb) { return cb.value; });
  return { years: years, pillars: pillars };
}

function setfUpdateDetailExportLink(qs) {
  const link = document.getElementById("setf-export-detail");
  if (!link) return;
  const base = link.href.split("?")[0];
  link.href = qs ? base + "?" + qs : base;
}

function setfRenderDetailTable(rows) {
  const tbody = document.querySelector("#setf-detail-table tbody");
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted)">Belum ada transaksi.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(function (r) {
    return "<tr>" +
      "<td>" + r.sumber + "</td>" +
      "<td>" + r.siswa_code + "</td>" +
      "<td>" + r.nama + "</td>" +
      "<td>" + r.tanggal + "</td>" +
      "<td>" + r.cat1 + "</td>" +
      "<td>" + (r.cat2 || "") + "</td>" +
      '<td class="num-right">' + setfFmtJutaan(r.amount) + "</td>" +
      "<td>" + (r.status || "") + "</td>" +
      "</tr>";
  }).join("");
}

function setfLoadDetailTransaksi() {
  const filters = setfGetDetailFilters();
  const qs = setfBuildQueryString(filters);
  setfUpdateDetailExportLink(qs);
  document.querySelector("#setf-detail-table tbody").innerHTML = skeletonRows(6, 8);
  fetch("/beasiswa/sahabat/api/all_transactions" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (resp) {
      if (!resp.ok) { showToast(resp.pesan || "Gagal memuat detail transaksi.", "error"); return; }
      setfRenderDetailTable(resp.rows);
    })
    .catch(function () { showToast("Gagal memuat detail transaksi.", "error"); });
}



function setfRenderKeluargaChart(families) {
    const xLabels = families.map(function (f) {
        if (f.members.length > 1) {
            return [f.label, f.members.map(function (m) { return setfFirstName(m.nama); }).join(", ")];
        }
        return setfFirstName(f.members[0].nama);
    });
    const kesBudget = [];
    const kesActual = [];
    const penBudget = [];
    const penActual = [];

    families.forEach(function(f) {
        let kb = 0, ka = 0, pb = 0, pa = 0;
        f.members.forEach(function(m) {
            if (m.kategori && m.kategori.includes("By Medical")) {
                kb += m.budget || 0;
                ka += m.realisasi || 0;
            } else {
                pb += m.budget || 0;
                pa += m.realisasi || 0;
            }
        });
        kesBudget.push(kb);
        kesActual.push(ka);
        penBudget.push(pb);
        penActual.push(pa);
    });

    const stackData = [
        { name: "Kesehatan", budget: kesBudget, realisasi: kesActual, originalName: "By Medical" },
        { name: "Pendidikan", budget: penBudget, realisasi: penActual, originalName: "By Pendidikan" }
    ];

    let mode = "all";
    const selectedMode = document.querySelector('input[name="setf-keluarga-mode"]:checked');
    if (selectedMode) mode = selectedMode.value;

    setfRenderStackedGroupedChart("chart-keluarga", xLabels, stackData, mode);
}






const setfTotalZonePlugin = {
  id: 'totalZone',
  beforeDraw: function(chart) {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const ctx = chart.ctx;
    const xAxis = chart.scales.x;
    const yAxisRight = chart.scales['y-right'];
    if (!xAxis || !yAxisRight) return;
    
    let totalIndex = -1;
    xAxis.getTicks().forEach((tick, i) => {
       if (tick.label === "TOTAL") totalIndex = i;
    });
    if (totalIndex === -1) return;
    
    const leftX = totalIndex === 0 ? xAxis.left : (xAxis.getPixelForTick(totalIndex - 1) + xAxis.getPixelForTick(totalIndex)) / 2;
    const rightX = xAxis.right;
    
    const topY = chart.chartArea.top;
    const bottomY = chart.chartArea.bottom;
    
    ctx.save();
    ctx.beginPath();
    ctx.setLineDash([5, 5]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = isDark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)";
    ctx.fillStyle = isDark ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.02)";
    ctx.rect(leftX, topY, rightX - leftX, bottomY - topY);
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }
};

const setfStackTotalPlugin = {
  id: 'customLabels',
  afterDatasetsDraw: function(chart) {
    const ctx = chart.ctx;
    ctx.save();
    
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    ctx.font = 'bold 10px sans-serif';
    ctx.fillStyle = isDark ? "#e2e8f0" : "#475569";
    ctx.textAlign = 'center';
    
    const metaMap = {};
    chart.data.datasets.forEach(function(dataset, i) {
      const meta = chart.getDatasetMeta(i);
      if (!meta.hidden && !dataset.label.includes("(Shadow)")) {
         const stackId = meta.stack || 'default';
         if (!metaMap[stackId]) metaMap[stackId] = [];
         metaMap[stackId].push({ index: i, meta: meta, data: dataset.data });
      }
    });

    const numDataPoints = chart.data.labels.length;
    const yBaseline = chart.scales.y.getPixelForValue(0);

    for (let stackId in metaMap) {
      const layers = metaMap[stackId];
      for (let j = 0; j < numDataPoints; j++) {
        let sum = 0;
        let lastValidMeta = null;
        let anyMeta = null; 
        
        for (let l = 0; l < layers.length; l++) {
           const val = layers[l].data[j];
           if (layers[l].meta.data[j]) anyMeta = layers[l].meta.data[j];
           if (val) {
              sum += val;
              lastValidMeta = layers[l].meta.data[j];
           }
        }
        
        if (sum > 0 && lastValidMeta) {
           ctx.textBaseline = 'bottom';
           const xPos = lastValidMeta.x;
           const yPos = chart.scales.y.getPixelForValue(sum);
           ctx.fillText(setfFmtJutaan(sum), xPos, yPos - 5);
        }
        
        if (anyMeta && (stackId === "StackBudget" || stackId === "StackRealisasi")) {
           ctx.textBaseline = 'top';
           ctx.font = '9px sans-serif';
           ctx.fillStyle = isDark ? "#94a3b8" : "#64748b";
           let lbl = stackId === "StackBudget" ? "B" : "R";
           if (chart.canvas.id.includes("tahunan")) lbl = stackId === "StackBudget" ? "Budget" : "Realisasi";
           ctx.fillText(lbl, anyMeta.x, yBaseline + 14);
        }
      }
    }
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

    let rawDatasets = [];
    labels.forEach(function(lbl, idx) {
        let b = budgets[idx] || 0;
        let r = realisasis[idx] || 0;
        let color = setfColorForCategory(lbl);
        if (canvasId.includes("pillar")) {
            if (lbl === "AGRI") color = "#10b981";
            else if (lbl === "APP") color = "#3b82f6";
            else if (lbl === "FINANCE") color = "#f59e0b";
            else if (lbl === "SETF") color = "#8b5cf6";
            else color = "#64748b";
        }
        
        rawDatasets.push({
            label: lbl + " (Budget)",
            data: [b],
            backgroundColor: color,
            borderColor: setfShadeColor(color, -20),
            borderWidth: 1,
            stack: "StackBudget",
            barPercentage: 0.8,
            categoryPercentage: 0.8
        });
        
        rawDatasets.push({
            label: lbl + " (Actual)",
            data: [r],
            backgroundColor: typeof pattern !== 'undefined' ? pattern.draw('diagonal-right-left', color) : color,
            borderColor: setfShadeColor(color, -20),
            borderWidth: 1,
            stack: "StackRealisasi",
            barPercentage: 0.8,
            categoryPercentage: 0.8
        });
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

    const dual = setfInjectDualYAxis(['Total'], rawDatasets, scalesCfg);
    if (dual.scales['y-right']) dual.scales['y-right'].stacked = true;

    setfCharts[canvasId] = new Chart(ctx, {
        type: "bar",
        data: { labels: dual.labels, datasets: dual.datasets },
        plugins: [ChartDataLabels, setfStackTotalPlugin, setfTotalZonePlugin],
        options: {
            responsive: true,
            layout: { padding: { top: 20, bottom: 25 } },
            plugins: {
                legend: { 
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: { 
                        color: textColor, boxWidth: 12,
                        filter: function(item, chart) { return !item.text.includes('(Shadow)'); }
                    }
                },
                datalabels: { display: false }
            },
            scales: dual.scales
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
