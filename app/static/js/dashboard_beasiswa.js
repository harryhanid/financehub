// static/js/dashboard_beasiswa.js
let dashCharts = {};
const DASH_BULAN_LABEL = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

const DASH_PALETTE = ["#6366f1", "#818cf8", "#f97316", "#06b6d4", "#10b981", "#f59e0b"];
const dashCategoryColorMap = {};
function dashColorForCategory(name) {
  if (!dashCategoryColorMap[name]) {
    const idx = Object.keys(dashCategoryColorMap).length % DASH_PALETTE.length;
    dashCategoryColorMap[name] = DASH_PALETTE[idx];
  }
  return dashCategoryColorMap[name];
}

function dashFmtJutaan(amount) {
  return fmtJutaan(amount);
}

function dashSisaCell(amount) {
  const cls = (amount || 0) < 0 ? ' class="setf-sisa-negative"' : "";
  return "<td" + cls + ">" + dashFmtJutaan(amount) + "</td>";
}

function dashMismatchCell(amount, mismatch) {
  const cls = mismatch ? ' class="setf-payment-mismatch"' : "";
  return "<td" + cls + ">" + dashFmtJutaan(amount) + "</td>";
}

function dashColorScaleAttr(value, min, max) {
  if (!value) return "";
  const alpha = max > min ? 0.12 + ((value - min) / (max - min)) * 0.4 : 0.35;
  return ' style="background-color:rgba(99,102,241,' + alpha.toFixed(2) + ')"';
}

const DASH_CAT_BADGE_CLASS = {
  "By Pendidikan": "badge-cat-by-pendidikan",
  "By Tunjangan": "badge-cat-by-tunjangan",
  "By Penelitian": "badge-cat-by-penelitian",
  "By Medical": "badge-cat-by-medical",
};
function dashCatBadge(cat1) {
  if (!cat1) return "";
  const cls = DASH_CAT_BADGE_CLASS[cat1] || "badge-cat-lainnya";
  return '<span class="budget-badge ' + cls + '">' + cat1 + "</span>";
}

function dashThemeColor(varName, fallback) {
  const page = document.querySelector(".budget-page");
  const val = page ? getComputedStyle(page).getPropertyValue(varName).trim() : "";
  return val || fallback;
}

function dashDatalabelFormatter(value) {
  return value ? dashFmtJutaan(value) : null;
}

function dashRenderBarChart(canvasId, labels, datasets, onBarClick) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (dashCharts[canvasId]) dashCharts[canvasId].destroy();
  dashCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    plugins: [ChartDataLabels],
    options: {
      responsive: true,
      onHover: function (evt, elements) {
        if (onBarClick && evt.native && evt.native.target) {
          evt.native.target.style.cursor = elements.length ? "pointer" : "default";
        }
      },
      onClick: function (evt, elements) {
        if (!elements.length || !onBarClick) return;
        onBarClick(elements[0].index);
      },
      plugins: {
        legend: { labels: { color: dashThemeColor("--text-primary", "#e2e8f0") } },
        datalabels: {
          anchor: "end",
          align: "top",
          color: dashThemeColor("--text-primary", "#e2e8f0"),
          font: { size: 10, weight: "600" },
          formatter: dashDatalabelFormatter,
        },
      },
      scales: {
        x: { ticks: { color: dashThemeColor("--text-secondary", "#94a3b8") }, grid: { color: "rgba(148,163,184,0.1)" } },
        y: {
          ticks: {
            color: dashThemeColor("--text-secondary", "#94a3b8"),
            callback: function (value) { return dashFmtJutaan(value); },
          },
          grid: { color: "rgba(148,163,184,0.1)" },
        },
      },
    },
  });
}

function dashExpandGrafik() {
  const details = document.getElementById("dash-grafik-accordion");
  if (!details) return;
  if (!details.open) details.open = true;
}

function dashHighlightMonthlyRow(bulanIndex) {
  dashExpandGrafik();
  const tbody = document.querySelector("#dash-monthly-table tbody");
  if (!tbody) return;
  const rows = tbody.querySelectorAll("tr");
  rows.forEach(function (tr) { tr.classList.remove("setf-row-highlight"); });
  const target = rows[bulanIndex];
  if (target) {
    target.classList.add("setf-row-highlight");
    target.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function dashRefetchLatestPayments() {
  const filters = dashGetSelectedFilters();
  const params = new URLSearchParams(dashBuildQueryString(filters));
  fetch("/beasiswa/api/dashboard/latest_payments?" + params.toString())
    .then(function (r) { return r.json(); })
    .then(function (data) { dashRenderLatestPaymentsTable(data.data); })
    .catch(function () { showToast("Gagal memuat 10 transaksi terakhir.", "error"); });
}

function dashRenderBudgetVsRealisasiChart(canvasId, labels, budgets, realisasis) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (dashCharts[canvasId]) dashCharts[canvasId].destroy();
  
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#e2e8f0" : "#475569";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";
  const percentColor = isDark ? "#fbbf24" : "#d97706"; // Amber

  const budgetColor = "rgba(148, 163, 184, 0.8)"; // Slate 400
  const realisasiColor = "rgba(59, 130, 246, 0.9)"; // Blue 500

  dashCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Budget",
          data: budgets,
          backgroundColor: budgetColor,
          borderRadius: 4,
        },
        {
          label: "Realisasi",
          data: realisasis,
          backgroundColor: realisasiColor,
          borderRadius: 4,
        }
      ]
    },
    plugins: [ChartDataLabels],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 35 } },
      interaction: {
        mode: 'index',
        intersect: false,
      },
      onClick: function (evt, elements) {
        if (!elements || !elements.length) return;
        const idx = elements[0].index;
        if (labels && labels[idx]) {
          dashExportKategori(labels[idx]);
        }
      },
      onHover: function (evt, elements) {
        evt.native.target.style.cursor = elements && elements.length ? "pointer" : "default";
      },
      plugins: {
        legend: { position: "top", labels: { color: textColor } },
        datalabels: {
          display: true,
          labels: {
            nominal: {
              align: 'end',
              anchor: 'end',
              color: textColor,
              font: { size: 10, weight: '500' },
              offset: function(context) {
                 if (context.datasetIndex === 1 && context.chart.data.datasets[0].data[context.dataIndex] > 0) {
                     return 12; // push up if percentage is shown
                 }
                 return 0;
              },
              formatter: function(value) {
                return value ? dashFmtJutaan(value) : "";
              }
            },
            percent: {
              align: 'end',
              anchor: 'end',
              color: percentColor,
              font: { size: 10, weight: 'bold' },
              offset: -4,
              formatter: function(value, context) {
                if (context.datasetIndex === 1) {
                  let budgetVal = context.chart.data.datasets[0].data[context.dataIndex];
                  if (budgetVal > 0) {
                    let pct = (value / budgetVal) * 100;
                    return '(' + pct.toFixed(1) + '%)';
                  }
                }
                return "";
              }
            }
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return context.dataset.label + ": " + dashFmtJutaan(context.raw);
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
            callback: function(value) { return dashFmtJutaan(value); }
          }
        },
        x: {
          grid: { display: false },
          ticks: { color: textColor }
        }
      }
    }
  });
}

function dashRenderDoughnutChart(canvasId, labels, values, colors) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (dashCharts[canvasId]) dashCharts[canvasId].destroy();
  dashCharts[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors }] },
    plugins: [ChartDataLabels],
    options: {
      responsive: true,
      plugins: {
        legend: { position: "right", labels: { color: dashThemeColor("--text-primary", "#e2e8f0") } },
        datalabels: {
          anchor: "center",
          align: "center",
          color: "#fff",
          font: { size: 10, weight: "600" },
          formatter: dashDatalabelFormatter,
        },
      },
    },
  });
}

function dashRenderSummaryCards(rows) {
  const totalSiswa = rows.filter(function (r) { return r.status === "Aktif"; }).length;
  const totalBudget = rows.reduce(function (s, r) { return s + r.budget_total; }, 0);
  const totalPayment = rows.reduce(function (s, r) { return s + r.payment_total; }, 0);
  const totalRealisasi = rows.reduce(function (s, r) { return s + r.realisasi_total; }, 0);
  const totalSisa = rows.reduce(function (s, r) { return s + r.sisa_budget; }, 0);
  const cards = [
    ["Total Siswa Aktif", totalSiswa, ""],
    ["Total Budget", dashFmtJutaan(totalBudget), " tint-budget"],
    ["Total Klaim", dashFmtJutaan(totalPayment), " tint-klaim"],
    ["Total Realisasi", dashFmtJutaan(totalRealisasi), " tint-realisasi"],
    ["Sisa Budget", dashFmtJutaan(totalSisa), totalSisa < 0 ? " tint-negative" : ""],
  ];
  document.getElementById("dash-summary").innerHTML = cards.map(function (c) {
    return '<div class="beasiswa-dash-stat-card' + c[2] + '"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
  }).join("");
}

function dashRenderSummarySkeleton() {
  document.getElementById("dash-summary").innerHTML = Array(5).fill(0).map(function () {
    return '<div class="beasiswa-dash-stat-card"><div class="label">&nbsp;</div>' +
      '<div class="fh-skel" style="width:70%;height:20px;margin-top:.25rem"></div></div>';
  }).join("");
}

function dashRenderProgramTable(rows) {
  const tbody = document.querySelector("#dash-program-table tbody");
  if (!rows || !rows.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data.</td></tr>';
    return;
  }
  const rowsHtml = rows.map(function (r) {
    return "<tr>" +
      "<td>" + r.program + "</td>" +
      '<td class="num-right">' + dashFmtJutaan(r.budget) + "</td>" +
      '<td class="num-right">' + dashFmtJutaan(r.realisasi) + "</td>" +
      '<td class="num-right"' + (r.sisa < 0 ? ' style="color:#dc2626"' : '') + '>' + dashFmtJutaan(r.sisa) + "</td>" +
      "</tr>";
  }).join("");
  
  const totalBudget = rows.reduce((acc, val) => acc + val.budget, 0);
  const totalRealisasi = rows.reduce((acc, val) => acc + val.realisasi, 0);
  const totalSisa = rows.reduce((acc, val) => acc + val.sisa, 0);
  
  const totalRow = "<tr style=\"font-weight:bold\"><td>Total</td>" +
    '<td class="num-right">' + dashFmtJutaan(totalBudget) + "</td>" +
    '<td class="num-right">' + dashFmtJutaan(totalRealisasi) + "</td>" +
    '<td class="num-right"' + (totalSisa < 0 ? ' style="color:#dc2626"' : '') + '>' + dashFmtJutaan(totalSisa) + "</td></tr>";
  
  tbody.innerHTML = rowsHtml + totalRow;
}

function dashRenderKategoriTable(kategoriRows) {
  const tbody = document.querySelector("#dash-kategori-table tbody");
  if (!kategoriRows || !kategoriRows.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data kategori.</td></tr>';
    return;
  }
  const rows = kategoriRows.map(function (k) {
    const sisa = k.budget - k.realisasi;
    return "<tr>" +
      "<td>" + dashCatBadge(k.cat1) + "</td>" +
      '<td class="num-right">' + dashFmtJutaan(k.budget) + "</td>" +
      '<td class="num-right">' + dashFmtJutaan(k.realisasi) + "</td>" +
      '<td class="num-right"' + (sisa < 0 ? ' style="color:#dc2626"' : '') + '>' + dashFmtJutaan(sisa) + "</td>" +
      "</tr>";
  }).join("");
  const totalBudget = kategoriRows.reduce(function (s, k) { return s + k.budget; }, 0);
  const totalRealisasi = kategoriRows.reduce(function (s, k) { return s + k.realisasi; }, 0);
  const sisa = totalBudget - totalRealisasi;
  const totalRow = "<tr style=\"font-weight:bold\"><td>Total</td>" +
    '<td class="num-right">' + dashFmtJutaan(totalBudget) + "</td>" +
    '<td class="num-right">' + dashFmtJutaan(totalRealisasi) + "</td>" +
    '<td class="num-right"' + (sisa < 0 ? ' style="color:#dc2626"' : '') + '>' + dashFmtJutaan(sisa) + "</td></tr>";
  tbody.innerHTML = rows + totalRow;
}

function dashRenderJenjangTable(jenjangRows) {
  const tbody = document.querySelector("#dash-jenjang-table tbody");
  if (!jenjangRows || !jenjangRows.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data jenjang studi.</td></tr>';
    return;
  }
  const rows = jenjangRows.map(function (j) {
    const sisa = j.budget - j.realisasi;
    return "<tr>" +
      "<td>" + dashCatBadge(j.jenjang) + "</td>" +
      '<td class="num-right">' + dashFmtJutaan(j.budget) + "</td>" +
      '<td class="num-right">' + dashFmtJutaan(j.realisasi) + "</td>" +
      '<td class="num-right"' + (sisa < 0 ? ' style="color:#dc2626"' : '') + '>' + dashFmtJutaan(sisa) + "</td>" +
      "</tr>";
  }).join("");
  const totalBudget = jenjangRows.reduce(function (s, j) { return s + j.budget; }, 0);
  const totalRealisasi = jenjangRows.reduce(function (s, j) { return s + j.realisasi; }, 0);
  const sisa = totalBudget - totalRealisasi;
  const totalRow = "<tr style=\"font-weight:bold\"><td>Total</td>" +
    '<td class="num-right">' + dashFmtJutaan(totalBudget) + "</td>" +
    '<td class="num-right">' + dashFmtJutaan(totalRealisasi) + "</td>" +
    '<td class="num-right"' + (sisa < 0 ? ' style="color:#dc2626"' : '') + '>' + dashFmtJutaan(sisa) + "</td>" +
    "</tr>";
  tbody.innerHTML = rows + totalRow;
}

function dashRenderPillarYearlyTable(pillarRows) {
  const tbody = document.querySelector("#dash-pillar-year-table tbody");
  const thead = document.querySelector("#dash-pillar-year-thead");
  
  if (!pillarRows || !pillarRows.length) {
    tbody.innerHTML = '<tr><td style="text-align:center;color:var(--text-muted)">Belum ada data.</td></tr>';
    return;
  }

  // Get unique years and unique pillars
  let yearSet = new Set();
  let pillarSet = new Set();
  let pillarTotals = {};
  let grandTotal = 0;
  
  pillarRows.forEach(row => {
    yearSet.add(row.tahun);
    Object.keys(row.pillars).forEach(p => {
      pillarSet.add(p);
      let val = row.pillars[p];
      pillarTotals[p] = (pillarTotals[p] || 0) + val;
      grandTotal += val;
    });
  });
  
  let yearNames = Array.from(yearSet).sort((a,b) => a - b); // Ascending
  let pillarNames = Array.from(pillarSet).sort();
  
  // Update header
  thead.innerHTML = "<th>PILLAR</th>" + yearNames.map(y => '<th class="num-right">' + y + "</th>").join("") + '<th class="num-right">Total</th><th class="num-right">%</th>';
  
  const rows = pillarNames.map(p => {
    let cells = yearNames.map(y => {
      let rowForYear = pillarRows.find(r => r.tahun === y);
      let val = rowForYear ? (rowForYear.pillars[p] || 0) : 0;
      return '<td class="num-right">' + dashFmtJutaan(val) + "</td>";
    }).join("");
    
    let pTotal = pillarTotals[p] || 0;
    let pct = grandTotal > 0 ? ((pTotal / grandTotal) * 100).toFixed(1) : "0.0";
    
    return "<tr><td><span class=\"budget-badge\" style=\"background:#eef2ff;color:#4f46e5;border:1px solid #c7d2fe;font-weight:600\">" + p + "</span></td>" + cells + 
           '<td class="num-right" style="font-weight:bold">' + dashFmtJutaan(pTotal) + "</td>" +
           '<td class="num-right" style="font-size:0.75rem;color:var(--text-muted)">' + pct + "%</td></tr>";
  }).join("");
  
  // Total row
  let totalsByYear = yearNames.map(y => {
    let rowForYear = pillarRows.find(r => r.tahun === y);
    let t = 0;
    if (rowForYear) {
       Object.values(rowForYear.pillars).forEach(v => { t += v; });
    }
    return '<td class="num-right">' + dashFmtJutaan(t) + "</td>";
  }).join("");
  const totalRow = '<tr style="background:#f8fafc;font-weight:bold"><td>Total</td>' + totalsByYear + 
                   '<td class="num-right">' + dashFmtJutaan(grandTotal) + '</td><td class="num-right" style="font-size:0.75rem">100%</td></tr>';
  
  tbody.innerHTML = rows + totalRow;
}

function dashRenderMonthlyChart(months, currentYear) {
  let prevYear = currentYear - 1;
  dashRenderBarChart("dash-chart-bulanan", months.map(function (m) { return DASH_BULAN_LABEL[m.bulan - 1]; }), [
    { type: "line", label: "Realisasi " + prevYear, data: months.map(function (m) { return m.realisasi_last_year || 0; }), borderColor: "#f97316", backgroundColor: "transparent", borderWidth: 2, tension: 0.3 },
    { type: "bar", label: "Realisasi " + currentYear, data: months.map(function (m) { return m.realisasi; }), backgroundColor: "#818cf8" }
  ], function (index) {
    dashHighlightMonthlyRow(index);
    if (months && months[index]) {
      dashExportTrendBulan(months[index].bulan);
    }
  });
}

function dashRenderMonthlyTable(comparison, years) {
  const theadRow = document.getElementById("dash-monthly-thead-row");
  theadRow.innerHTML = "<th>Bulan</th>" + years.map(function (y) { return "<th>" + y + "</th>"; }).join("");

  const tbody = document.querySelector("#dash-monthly-table tbody");
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
      return "<td" + dashColorScaleAttr(v, minVal, maxVal) + ">" + dashFmtJutaan(v) + "</td>";
    }).join("");
    return "<tr><td>" + DASH_BULAN_LABEL[row.bulan - 1] + "</td>" + cells + "</tr>";
  }).join("");
  const totalCells = years.map(function (y) {
    const total = comparison.reduce(function (s, row) { return s + (row.per_tahun[y] || 0); }, 0);
    return "<td>" + dashFmtJutaan(total) + "</td>";
  }).join("");
  const totalRow = "<tr style=\"font-weight:bold\"><td>Total</td>" + totalCells + "</tr>";
  tbody.innerHTML = rows + totalRow;
}

function dashRenderYearlyChart(yearly) {
  if (!yearly || !yearly.length) {
    if (dashCharts["dash-chart-tahunan"]) { dashCharts["dash-chart-tahunan"].destroy(); delete dashCharts["dash-chart-tahunan"]; }
    return;
  }
  const years = yearly.map(function (y) { return y.tahun; });
  dashRenderBarChart("dash-chart-tahunan", years, [
    { label: "Realisasi", data: yearly.map(function (y) { return y.realisasi; }), backgroundColor: "#10b981" },
  ], function (index) {
    const selectedYear = years[index];
    dashExportTrendTahun(selectedYear);
  });
}

function dashExportTrendTahun(specificYear) {
  const filters = dashGetSelectedFilters();
  const exportFilters = { ...filters, years: [] };
  const params = new URLSearchParams(dashBuildQueryString(exportFilters));
  if (specificYear) {
    params.set("year", specificYear);
  }
  window.location.href = "/beasiswa/api/dashboard/export_trend_tahunan?" + params.toString();
}

function dashExportTrendBulan(specificBulan) {
  const filters = dashGetSelectedFilters();
  const params = new URLSearchParams(dashBuildQueryString(filters));
  if (specificBulan) {
    params.set("bulan", specificBulan);
  }
  window.location.href = "/beasiswa/api/dashboard/export_trend_bulanan?" + params.toString();
}

function dashExportKategori(specificCat1) {
  const filters = dashGetSelectedFilters();
  const params = new URLSearchParams(dashBuildQueryString(filters));
  if (specificCat1) {
    params.set("cat1", specificCat1);
  }
  window.location.href = "/beasiswa/api/dashboard/export_kategori?" + params.toString();
}


const DASH_PAYMENT_STATUS_BADGE = {
  open:     '<span style="background:#fef3c7;color:#d97706;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:600">Open</span>',
  complete: '<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:600">Complete</span>',
};
function dashPaymentStatusBadge(status) {
  return DASH_PAYMENT_STATUS_BADGE[status] || status || "";
}

function dashRenderLatestPaymentsTable(rows) {
  const tbody = document.querySelector("#dash-latest-payments-table tbody");
  if (!rows || !rows.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Belum ada transaksi.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(function (r) {
    return "<tr>" +
      "<td>" + r.tanggal + "</td>" +
      "<td>" + r.nama + "</td>" +
      "<td>" + dashCatBadge(r.cat1) + "</td>" +
      "<td>" + (r.cat2 || "") + "</td>" +
      '<td class="num-right">' + dashFmtJutaan(r.amount) + "</td>" +
      "<td>" + dashPaymentStatusBadge(r.status) + "</td>" +
      "</tr>";
  }).join("");
}

function dashGetSelectedFilters() {
  const years = Array.from(document.querySelectorAll(".dash-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillars = Array.from(document.querySelectorAll(".dash-pillar-cb:checked")).map(function (cb) { return cb.value; });
  const programs = Array.from(document.querySelectorAll(".dash-program-cb:checked")).map(function (cb) { return cb.value; });
  const jenjangs = Array.from(document.querySelectorAll(".dash-jenjang-cb:checked")).map(function (cb) { return cb.value; });
  const angkatans = Array.from(document.querySelectorAll(".dash-angkatan-cb:checked")).map(function (cb) { return cb.value; });
  const statuses = Array.from(document.querySelectorAll(".dash-status-cb:checked")).map(function (cb) { return cb.value; });
  return { years: years, pillars: pillars, programs: programs, jenjangs: jenjangs, angkatans: angkatans, statuses: statuses };
}

function dashBuildQueryString(filters) {
  const params = new URLSearchParams();
  if (filters.years && filters.years.length) params.set("years", filters.years.join(","));
  if (filters.pillars && filters.pillars.length) params.set("pillars", filters.pillars.join(","));
  if (filters.programs && filters.programs.length) params.set("programs", filters.programs.join(","));
  if (filters.jenjangs && filters.jenjangs.length) params.set("jenjangs", filters.jenjangs.join(","));
  if (filters.angkatans && filters.angkatans.length) params.set("angkatans", filters.angkatans.join(","));
  if (filters.statuses && filters.statuses.length) params.set("statuses", filters.statuses.join(","));
  return params.toString();
}


function dashApplyFilters() {
  const filters = dashGetSelectedFilters();
  const qs = dashBuildQueryString(filters);

  dashRenderSummarySkeleton();
  document.querySelector("#dash-kategori-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#dash-latest-payments-table tbody").innerHTML = skeletonRows(5, 6);
  document.querySelector("#dash-pillar-year-table tbody").innerHTML = skeletonRows(4, 2);
  document.querySelector("#dash-program-table tbody").innerHTML = skeletonRows(4, 4);

  dashRefetchLatestPayments();

  fetch("/beasiswa/api/dashboard/summary" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      dashRenderSummaryCards(data.data);
    })
    .catch(function () { showToast("Gagal memuat ringkasan.", "error"); });
    
  fetch("/beasiswa/api/dashboard/program_summary" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      dashRenderProgramTable(data.data);
    })
    .catch(function () { showToast("Gagal memuat detail program.", "error"); });

  fetch("/beasiswa/api/dashboard/breakdown" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      let labels = data.data.kategori.map(function (k) { return k.cat1 || "Tanpa Kategori"; });
      let budgets = data.data.kategori.map(function (k) { return k.budget; });
      let realisasis = data.data.kategori.map(function (k) { return k.realisasi; });
      
      let totalBudget = budgets.reduce((a, b) => a + b, 0);
      let totalRealisasi = realisasis.reduce((a, b) => a + b, 0);
      
      labels.push("Total");
      budgets.push(totalBudget);
      realisasis.push(totalRealisasi);
      
      dashRenderBudgetVsRealisasiChart("dash-chart-kategori", labels, budgets, realisasis);
      dashRenderKategoriTable(data.data.kategori);
      dashRenderJenjangTable(data.data.jenjang);
    })
    .catch(function () { showToast("Gagal memuat breakdown kategori.", "error"); });
    
  fetch("/beasiswa/api/dashboard/pillar_yearly" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      dashRenderPillarYearlyTable(data.data);
      let yearlyData = data.data.map(d => ({tahun: d.tahun, realisasi: Object.values(d.pillars).reduce((a, b) => a + b, 0)}));
      yearlyData.sort((a, b) => a.tahun - b.tahun);
      dashRenderYearlyChart(yearlyData);
    })
    .catch(function () { showToast("Gagal memuat data pillar bulanan.", "error"); });

  if (filters.years.length) {
    document.querySelector("#dash-monthly-table tbody").innerHTML = skeletonRows(2, 4);
    fetch("/beasiswa/api/dashboard/monthly?" + qs)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        dashRenderMonthlyChart(data.data.months, data.data.chart_year);
        dashRenderMonthlyTable(data.data.comparison, filters.years);
      })
      .catch(function () { showToast("Gagal memuat data bulanan.", "error"); });
  } else {
    if (dashCharts["dash-chart-bulanan"]) { dashCharts["dash-chart-bulanan"].destroy(); delete dashCharts["dash-chart-bulanan"]; }
    dashRenderMonthlyTable([], []);
  }
}

function initDashboard() {
  // Hanya inisialisasi satu kali
  if (window._dashInitialized) return;
  window._dashInitialized = true;

  initFilterChips(document, dashApplyFilters);
  dashApplyFilters();
}

window.addEventListener("fh-theme-changed", function () {
  if (dashCharts["dash-chart-kategori"] || dashCharts["dash-chart-bulanan"] || dashCharts["dash-chart-tahunan"]) {
    dashApplyFilters();
  }
});
