// static/js/sahabat_etf.js
let setfCharts = {};

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
    ["Total Siswa Aktif", totalSiswa],
    ["Total Budget", fmtRupiah(totalBudget)],
    ["Total Payment", fmtRupiah(totalPayment)],
    ["Total Realisasi", fmtRupiah(totalRealisasi)],
    ["Sisa Budget", fmtRupiah(totalSisa)],
  ];
  document.getElementById("setf-summary").innerHTML = cards.map(function (c) {
    return '<div class="budget-stat-card"><div class="label">' + c[0] +
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

function initSahabatEtf() {
  fetch("/beasiswa/sahabat/api/summary")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      const rows = data.rows;
      setfRenderSummaryCards(rows);
      setfRenderTable(rows);
      setfRenderBarChart("chart-siswa", rows.map(function (r) { return r.nama; }), [
        { label: "Budget", data: rows.map(function (r) { return r.budget_total; }), backgroundColor: "#6366f1" },
        { label: "Realisasi", data: rows.map(function (r) { return r.realisasi_total; }), backgroundColor: "#818cf8" },
      ]);
    })
    .catch(function () { showToast("Gagal memuat ringkasan siswa.", "error"); });

  fetch("/beasiswa/sahabat/api/breakdown")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfRenderDoughnutChart("chart-kategori",
        data.kategori.map(function (k) { return k.cat1; }),
        data.kategori.map(function (k) { return k.realisasi; }),
        ["#6366f1", "#818cf8", "#f97316", "#06b6d4", "#10b981", "#f59e0b"]);
      setfRenderAlert(data.over_budget);
    })
    .catch(function () { showToast("Gagal memuat breakdown kategori.", "error"); });
}
