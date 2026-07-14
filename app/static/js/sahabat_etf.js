// static/js/sahabat_etf.js
let setfCharts = {};
const SETF_BULAN_LABEL = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

function setfRenderBarChart(canvasId, labels, datasets) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#e2e8f0" } } },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
      },
    },
  });
}

function setfRenderDoughnutChart(canvasId, labels, values, colors) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  setfCharts[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors }] },
    options: { responsive: true, plugins: { legend: { labels: { color: "#e2e8f0" } } } },
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
    ["Total Budget", fmtRupiah(totalBudget), ""],
    ["Total Payment", fmtRupiah(totalPayment), ""],
    ["Total Realisasi", fmtRupiah(totalRealisasi), " setf-stat-realisasi"],
    ["Sisa Budget", fmtRupiah(totalSisa), ""],
  ];
  document.getElementById("setf-summary").innerHTML = cards.map(function (c) {
    return '<div class="budget-stat-card' + c[2] + '"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
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
      "<td>" + fmtRupiah(r.budget_total) + "</td>" +
      "<td>" + fmtRupiah(r.payment_total) + "</td>" +
      "<td>" + fmtRupiah(r.realisasi_total) + "</td>" +
      "<td>" + fmtRupiah(r.sisa_budget) + "</td>" +
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
      "<td>" + fmtRupiah(k.budget) + "</td>" +
      "<td>" + fmtRupiah(k.realisasi) + "</td>" +
      "<td>" + fmtRupiah(sisa) + "</td>" +
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
    return "<li>" + o.nama + " — realisasi melebihi budget sebesar " + fmtRupiah(o.selisih) + "</li>";
  }).join("");
}

function setfRenderMonthlyChart(months) {
  setfRenderBarChart("chart-bulanan", months.map(function (m) { return SETF_BULAN_LABEL[m.bulan - 1]; }), [
    { label: "Budget", data: months.map(function (m) { return m.budget; }), backgroundColor: "#6366f1" },
    { label: "Realisasi", data: months.map(function (m) { return m.realisasi; }), backgroundColor: "#818cf8" },
  ]);
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
    const cells = years.map(function (y) { return "<td>" + fmtRupiah(row.per_tahun[y] || 0) + "</td>"; }).join("");
    return "<tr><td>" + SETF_BULAN_LABEL[row.bulan - 1] + "</td>" + cells + "</tr>";
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
        ["#6366f1", "#818cf8", "#f97316", "#06b6d4", "#10b981", "#f59e0b"]);
      setfRenderKategoriTable(data.kategori);
      setfRenderAlert(data.over_budget);
    })
    .catch(function () { showToast("Gagal memuat breakdown kategori.", "error"); });

  if (filters.years.length) {
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
