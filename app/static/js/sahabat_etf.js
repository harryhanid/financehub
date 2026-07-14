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
  return jt.toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + " Jt";
}

function setfThemeColor(varName, fallback) {
  const page = document.querySelector(".budget-page");
  const val = page ? getComputedStyle(page).getPropertyValue(varName).trim() : "";
  return val || fallback;
}

function setfRenderBarChart(canvasId, labels, datasets, onBarClick) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    options: {
      responsive: true,
      onClick: function (evt, elements) {
        if (!elements.length || !onBarClick) return;
        onBarClick(elements[0].index);
      },
      plugins: { legend: { labels: { color: setfThemeColor("--text-primary", "#e2e8f0") } } },
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
    options: {
      responsive: true,
      onClick: function (evt, elements) {
        if (!elements.length) return;
        setfSetKategoriDrilldown(labels[elements[0].index]);
      },
      plugins: { legend: { position: "right", labels: { color: setfThemeColor("--text-primary", "#e2e8f0") } } },
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
    ["Total Siswa Aktif", totalSiswa, ""],
    ["Total Budget", setfFmtJutaan(totalBudget), ""],
    ["Total Payment", setfFmtJutaan(totalPayment), ""],
    ["Total Realisasi", setfFmtJutaan(totalRealisasi), " setf-stat-realisasi"],
    ["Sisa Budget", setfFmtJutaan(totalSisa), ""],
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
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted)">Belum ada siswa Sahabat ETF.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(function (r) {
    return "<tr>" +
      "<td>" + r.nama + "</td>" +
      "<td>" + r.jenjang + "</td>" +
      "<td>" + r.angkatan + "</td>" +
      "<td>" + r.status + "</td>" +
      "<td>" + setfFmtJutaan(r.budget_total) + "</td>" +
      "<td>" + setfFmtJutaan(r.payment_total) + "</td>" +
      "<td>" + setfFmtJutaan(r.realisasi_total) + "</td>" +
      "<td>" + setfFmtJutaan(r.sisa_budget) + "</td>" +
      "</tr>";
  }).join("");
}

function setfRenderKategoriTable(kategoriRows) {
  const tbody = document.querySelector("#setf-kategori-table tbody");
  if (!kategoriRows.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data kategori.</td></tr>';
    return;
  }
  tbody.innerHTML = kategoriRows.map(function (k) {
    const sisa = k.budget - k.realisasi;
    return "<tr>" +
      "<td>" + k.cat1 + "</td>" +
      "<td>" + setfFmtJutaan(k.budget) + "</td>" +
      "<td>" + setfFmtJutaan(k.realisasi) + "</td>" +
      "<td>" + setfFmtJutaan(sisa) + "</td>" +
      "</tr>";
  }).join("");
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
    { label: "Budget", data: months.map(function (m) { return m.budget; }), backgroundColor: "#6366f1" },
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
  tbody.innerHTML = comparison.map(function (row) {
    const cells = years.map(function (y) { return "<td>" + setfFmtJutaan(row.per_tahun[y] || 0) + "</td>"; }).join("");
    return "<tr><td>" + SETF_BULAN_LABEL[row.bulan - 1] + "</td>" + cells + "</tr>";
  }).join("");
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
  tbody.innerHTML = pillarRows.map(function (p) {
    return "<tr>" +
      "<td>" + p.pillar + "</td>" +
      "<td>" + setfFmtJutaan(p.budget) + "</td>" +
      "<td>" + setfFmtJutaan(p.realisasi) + "</td>" +
      "<td>" + setfFmtJutaan(p.sisa) + "</td>" +
      "</tr>";
  }).join("");
}

function setfRenderLatestPaymentsTable(rows) {
  const tbody = document.querySelector("#setf-latest-payments-table tbody");
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada transaksi.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(function (r) {
    return "<tr>" +
      "<td>" + r.tanggal + "</td>" +
      "<td>" + r.nama + "</td>" +
      "<td>" + r.cat1 + "</td>" +
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

function setfApplyFilters() {
  const filters = setfGetSelectedFilters();
  const qs = setfBuildQueryString(filters);
  setfUpdateExportLinks(qs);

  setfActiveKategoriDrilldown = null;
  setfRenderDrilldownChip();

  setfRenderSummarySkeleton();
  document.querySelector("#setf-table tbody").innerHTML = skeletonRows(8, 6);
  document.querySelector("#setf-kategori-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-latest-payments-table tbody").innerHTML = skeletonRows(4, 6);
  document.querySelector("#setf-pillar-table tbody").innerHTML = skeletonRows(4, 4);

  setfRefetchLatestPayments();

  fetch("/beasiswa/sahabat/api/summary" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfRenderSummaryCards(data.rows);
      setfRenderTable(data.rows);
    })
    .catch(function () { showToast("Gagal memuat ringkasan siswa.", "error"); });

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
  setfApplyFilters();
}

window.addEventListener("fh-theme-changed", function () {
  if (setfCharts["chart-kategori"] || setfCharts["chart-bulanan"] || setfCharts["chart-tahunan"]) {
    setfApplyFilters();
  }
});
