// static/js/sahabat_etf.js
let setfCharts = {};
const SETF_BULAN_LABEL = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

const SETF_PALETTE = ["#6366f1", "#818cf8", "#f97316", "#06b6d4", "#10b981", "#f59e0b"];
const setfCategoryColorMap = {};
function setfColorForCategory(name) {
  if (!setfCategoryColorMap[name]) {
    const idx = Object.keys(setfCategoryColorMap).length % SETF_PALETTE.length;
    setfCategoryColorMap[name] = SETF_PALETTE[idx];
  }
  return setfCategoryColorMap[name];
}

function setfFmtJutaan(amount) {
  const jt = (amount || 0) / 1000000;
  return jt.toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
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
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    plugins: [ChartDataLabels],
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
        x: { ticks: { color: setfThemeColor("--text-secondary", "#94a3b8") }, grid: { color: "rgba(148,163,184,0.1)" } },
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

const setfStackTotalPlugin = {
  id: "setfStackTotal",
  afterDatasetsDraw: function (chart) {
    const totals = {};
    chart.data.datasets.forEach(function (ds) {
      ds.data.forEach(function (v, i) { totals[i] = (totals[i] || 0) + (v || 0); });
    });
    const meta = chart.getDatasetMeta(0);
    if (!meta || !meta.data.length) return;
    const ctx = chart.ctx;
    const yScale = chart.scales.y;
    ctx.save();
    ctx.font = "bold 10px sans-serif";
    ctx.fillStyle = setfThemeColor("--text-primary", "#e2e8f0");
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    meta.data.forEach(function (bar, i) {
      const total = totals[i] || 0;
      if (!total) return;
      ctx.fillText(setfFmtJutaan(total), bar.x, yScale.getPixelForValue(total) - 4);
    });
    ctx.restore();
  },
};

function setfRenderStackedBarChart(canvasId, families) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();

  const maxMembers = families.reduce(function (m, f) { return Math.max(m, f.members.length); }, 0);
  const datasets = [];
  for (let i = 0; i < maxMembers; i++) {
    const fill = SETF_PALETTE[i % SETF_PALETTE.length];
    datasets.push({
      label: "Anggota " + (i + 1),
      data: families.map(function (f) { return i < f.members.length ? f.members[i].realisasi : null; }),
      backgroundColor: fill,
      borderColor: setfShadeColor(fill, -25),
      borderWidth: 2,
      borderSkipped: false,
    });
  }

  const xLabels = families.map(function (f) {
    if (f.members.length > 1) {
      return [f.label, f.members.map(function (m) { return setfFirstName(m.nama); }).join(", ")];
    }
    return setfFirstName(f.members[0].nama);
  });

  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: xLabels, datasets: datasets },
    plugins: [ChartDataLabels, setfStackTotalPlugin],
    options: {
      responsive: true,
      layout: { padding: { top: 20 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (item) {
              const member = families[item.dataIndex].members[item.datasetIndex];
              return member ? member.nama + ": " + setfFmtJutaan(member.realisasi) : "";
            },
          },
        },
        datalabels: {
          anchor: "center",
          align: "center",
          color: "#fff",
          font: { size: 9, weight: "600" },
          formatter: setfDatalabelFormatter,
        },
      },
      scales: {
        x: {
          stacked: true,
          ticks: { color: setfThemeColor("--text-secondary", "#94a3b8") },
          grid: { color: "rgba(148,163,184,0.1)" },
        },
        y: {
          stacked: true,
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

function setfRenderFamilyTable(families) {
  const tbody = document.querySelector("#setf-family-table tbody");
  if (!families.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data keluarga.</td></tr>';
    return;
  }
  tbody.innerHTML = families.map(function (f) {
    const memberRows = f.members.map(function (m) {
      return "<tr><td>" + f.label + "</td><td>" + m.nama + "</td>" +
        "<td>" + setfCatBadgeList(m.kategori) + "</td>" +
        '<td class="num-right">' + setfFmtJutaan(m.realisasi) + "</td></tr>";
    }).join("");
    const totalRow = "<tr style=\"font-weight:bold\"><td>" + f.label + " — Total</td><td></td><td></td>" +
      '<td class="num-right">' + setfFmtJutaan(f.total_realisasi) + "</td></tr>";
    return memberRows + totalRow;
  }).join("");
}

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

function setfRenderDoughnutChart(canvasId, labels, values, colors) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  setfCharts[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors }] },
    plugins: [ChartDataLabels],
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
    setfSisaCell(totalSisa) + "</tr>";
  tbody.innerHTML = rowsHtml + totalRow;
}

function setfRenderKategoriTable(kategoriRows) {
  const tbody = document.querySelector("#setf-kategori-table tbody");
  if (!kategoriRows.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data kategori.</td></tr>';
    return;
  }
  const rows = kategoriRows.map(function (k) {
    const sisa = k.budget - k.realisasi;
    return "<tr>" +
      "<td>" + setfCatBadge(k.cat1) + "</td>" +
      "<td>" + setfFmtJutaan(k.budget) + "</td>" +
      "<td>" + setfFmtJutaan(k.realisasi) + "</td>" +
      setfSisaCell(sisa) +
      "</tr>";
  }).join("");
  const totalBudget = kategoriRows.reduce(function (s, k) { return s + k.budget; }, 0);
  const totalRealisasi = kategoriRows.reduce(function (s, k) { return s + k.realisasi; }, 0);
  const totalRow = "<tr style=\"font-weight:bold\"><td>Total</td>" +
    "<td>" + setfFmtJutaan(totalBudget) + "</td>" +
    "<td>" + setfFmtJutaan(totalRealisasi) + "</td>" +
    setfSisaCell(totalBudget - totalRealisasi) + "</tr>";
  tbody.innerHTML = rows + totalRow;
}

function setfRenderAlert(overBudget) {
  const card = document.getElementById("setf-alert-card");
  const list = document.getElementById("setf-alert-list");
  if (!overBudget.length) {
    card.style.display = "none";
    return;
  }
  card.style.display = "block";
  list.innerHTML = overBudget.map(function (o) {
    return "<li>" + o.nama + " — realisasi melebihi budget sebesar " + setfFmtJutaan(o.selisih) + "</li>";
  }).join("");
}

function setfRenderMonthlyChart(months) {
  setfRenderBarChart("chart-bulanan", months.map(function (m) { return SETF_BULAN_LABEL[m.bulan - 1]; }), [
    { label: "Realisasi", data: months.map(function (m) { return m.realisasi; }), backgroundColor: "#818cf8" },
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

function setfRenderYearlyChart(yearly) {
  if (!yearly || !yearly.length) {
    if (setfCharts["chart-tahunan"]) { setfCharts["chart-tahunan"].destroy(); delete setfCharts["chart-tahunan"]; }
    return;
  }
  setfRenderBarChart("chart-tahunan", yearly.map(function (y) { return y.tahun; }), [
    { label: "Realisasi", data: yearly.map(function (y) { return y.realisasi; }), backgroundColor: "#10b981" },
  ]);
}

function setfRenderPillarTable(pillarRows) {
  const tbody = document.querySelector("#setf-pillar-table tbody");
  if (!pillarRows.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data pillar.</td></tr>';
    return;
  }
  const rows = pillarRows.map(function (p) {
    return "<tr>" +
      "<td>" + p.pillar + "</td>" +
      "<td>" + setfFmtJutaan(p.budget) + "</td>" +
      "<td>" + setfFmtJutaan(p.realisasi) + "</td>" +
      setfSisaCell(p.sisa) +
      "</tr>";
  }).join("");
  const totalBudget = pillarRows.reduce(function (s, p) { return s + p.budget; }, 0);
  const totalRealisasi = pillarRows.reduce(function (s, p) { return s + p.realisasi; }, 0);
  const totalSisa = pillarRows.reduce(function (s, p) { return s + p.sisa; }, 0);
  const totalRow = "<tr style=\"font-weight:bold\"><td>Total</td>" +
    "<td>" + setfFmtJutaan(totalBudget) + "</td>" +
    "<td>" + setfFmtJutaan(totalRealisasi) + "</td>" +
    setfSisaCell(totalSisa) + "</tr>";
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
  const detailLink = document.getElementById("setf-export-detail");
  const baseSummary = summaryLink.href.split("?")[0];
  const baseDetail = detailLink.href.split("?")[0];
  summaryLink.href = qs ? baseSummary + "?" + qs : baseSummary;
  detailLink.href = qs ? baseDetail + "?" + qs : baseDetail;
}

function setfUpdateReportExportLink() {
  const sel = document.getElementById("setf-report-year");
  const link = document.getElementById("setf-export-report");
  if (!sel || !link) return;
  link.href = "/beasiswa/sahabat/export/report?year=" + encodeURIComponent(sel.value);
}

function setfExportPdf() {
  const accordions = document.querySelectorAll(".setf-accordion");
  const prevState = Array.from(accordions).map(function (d) { return d.open; });
  accordions.forEach(function (d) { d.open = true; });

  function resizeCharts() {
    Object.keys(setfCharts).forEach(function (key) {
      if (setfCharts[key]) setfCharts[key].resize();
    });
  }
  function onBeforePrint() { resizeCharts(); }
  function restore() {
    accordions.forEach(function (d, i) { d.open = prevState[i]; });
    window.removeEventListener("beforeprint", onBeforePrint);
    window.removeEventListener("afterprint", restore);
  }
  window.addEventListener("beforeprint", onBeforePrint);
  window.addEventListener("afterprint", restore);

  // Let the DOM reflow after opening the accordions (which can change chart
  // container widths) before charts resize and the print snapshot is taken.
  resizeCharts();
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      resizeCharts();
      window.print();
    });
  });
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
      setfRenderStackedBarChart("chart-keluarga", data.families);
      setfRenderFamilyTable(data.families);
    })
    .catch(function () { showToast("Gagal memuat data keluarga.", "error"); });

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
      setfRenderDoughnutChart("chart-kategori",
        data.kategori.map(function (k) { return k.cat1; }),
        data.kategori.map(function (k) { return k.realisasi; }),
        data.kategori.map(function (k) { return setfColorForCategory(k.cat1); }));
      setfRenderKategoriTable(data.kategori);
      setfRenderAlert(data.over_budget);
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

function initSahabatEtf() {
  document.querySelectorAll(".setf-year-cb").forEach(function (cb) {
    cb.addEventListener("change", setfApplyFilters);
  });
  document.querySelectorAll(".setf-pillar-cb").forEach(function (cb) {
    cb.addEventListener("change", setfApplyFilters);
  });
  const selectAllBtn = document.getElementById("setf-year-select-all");
  if (selectAllBtn) {
    selectAllBtn.addEventListener("click", function () {
      document.querySelectorAll(".setf-year-cb").forEach(function (cb) { cb.checked = true; });
      setfApplyFilters();
    });
  }
  const reportYearSelect = document.getElementById("setf-report-year");
  if (reportYearSelect) {
    reportYearSelect.addEventListener("change", setfUpdateReportExportLink);
    setfUpdateReportExportLink();
  }
  setfApplyFilters();
}

window.addEventListener("fh-theme-changed", function () {
  if (setfCharts["chart-kategori"] || setfCharts["chart-bulanan"] || setfCharts["chart-tahunan"] || setfCharts["chart-keluarga"]) {
    setfApplyFilters();
  }
});
