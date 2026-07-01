// static/js/budget.js — Budget Monitoring dashboard (Chart.js rendering)
let budgetCharts = {};

function budgetCurrentFilters() {
  return {
    company: document.getElementById("bf-company").value,
    dept: document.getElementById("bf-dept").value,
    year: document.getElementById("bf-year").value,
    category: document.getElementById("bf-category").value,
    activity: document.getElementById("bf-activity").value,
  };
}

function budgetFillSelect(id, values, keepFirst) {
  const el = document.getElementById(id);
  const first = el.options[0];
  el.innerHTML = "";
  el.appendChild(first);
  values.forEach(function (v) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    el.appendChild(opt);
  });
}

function budgetRenderBarChart(canvasId, labels, datasets) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (budgetCharts[canvasId]) budgetCharts[canvasId].destroy();
  budgetCharts[canvasId] = new Chart(ctx, {
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

function budgetRenderPieChart(canvasId, labels, values, colors) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (budgetCharts[canvasId]) budgetCharts[canvasId].destroy();
  budgetCharts[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors }] },
    options: { responsive: true, plugins: { legend: { labels: { color: "#e2e8f0" } } } },
  });
}

function budgetRenderSummary(summary) {
  const el = document.getElementById("budget-summary");
  const cards = [
    ["Total Budget", summary.formatted.totalBudget],
    ["Total Realisasi", summary.formatted.totalRealized],
    ["Sisa", summary.formatted.remaining],
    ["Utilisasi Rata-rata", summary.formatted.avgUtilization],
    ["Expired", summary.totalExpired],
    ["Near Limit", summary.totalNearLimit],
    ["Active", summary.totalActive],
  ];
  el.innerHTML = cards.map(function (c) {
    return '<div class="budget-stat-card"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
  }).join("");
}

function budgetRenderNotifications(notifications) {
  const el = document.getElementById("budget-notifications");
  el.innerHTML = "";
  if (!notifications.length) {
    const empty = document.createElement("li");
    empty.textContent = "Tidak ada notifikasi.";
    el.appendChild(empty);
    return;
  }
  notifications.forEach(function (n) {
    const li = document.createElement("li");
    const strong = document.createElement("strong");
    strong.textContent = n.title + ":";
    li.appendChild(strong);
    li.appendChild(document.createTextNode(" " + n.message));
    el.appendChild(li);
  });
}

function budgetLoadLookups() {
  return fetch("/budget/api/lookups")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      budgetFillSelect("bf-dept", data.departments);
      budgetFillSelect("bf-year", data.years);
      budgetFillSelect("bf-category", data.categories);
      budgetFillSelect("bf-activity", data.activities);
    })
    .catch(function () {
      showToast("Gagal memuat filter dashboard.", "error");
    });
}

function budgetLoadDashboard() {
  const params = new URLSearchParams(budgetCurrentFilters());
  return fetch("/budget/api/dashboard-data?" + params.toString())
    .then(function (r) { return r.json(); })
    .then(function (data) {
      budgetRenderSummary(data.summary);
      budgetRenderNotifications(data.notifications);
      budgetRenderBarChart("chart-monthly", data.monthlyChart.labels, [
        { label: "Budget", data: data.monthlyChart.budget, backgroundColor: "#6366f1" },
        { label: "Realisasi", data: data.monthlyChart.realized, backgroundColor: "#818cf8" },
      ]);
      budgetRenderBarChart("chart-dept", data.deptChart.labels, [
        { label: "Budget", data: data.deptChart.budget, backgroundColor: "#6366f1" },
        { label: "Realisasi", data: data.deptChart.realized, backgroundColor: "#818cf8" },
      ]);
      budgetRenderBarChart("chart-activity", data.activityChart.labels, [
        { label: "Budget", data: data.activityChart.budget, backgroundColor: "#6366f1" },
        { label: "Realisasi", data: data.activityChart.realized, backgroundColor: "#818cf8" },
      ]);
      budgetRenderBarChart("chart-category", data.categoryChart.labels, [
        { label: "Budget", data: data.categoryChart.budget, backgroundColor: "#6366f1" },
        { label: "Realisasi", data: data.categoryChart.realized, backgroundColor: "#818cf8" },
      ]);
      budgetRenderPieChart("chart-company", data.companyChart.labels, data.companyChart.budget,
        ["#f97316", "#06b6d4"]);
      budgetRenderPieChart("chart-status", data.statusChart.labels, data.statusChart.values,
        ["#10b981", "#f59e0b", "#ef4444", "#3b82f6"]);
    })
    .catch(function () {
      showToast("Gagal memuat data dashboard.", "error");
    });
}

function initBudgetDashboard() {
  budgetLoadLookups().then(budgetLoadDashboard);
  document.getElementById("bf-apply").addEventListener("click", budgetLoadDashboard);
}
