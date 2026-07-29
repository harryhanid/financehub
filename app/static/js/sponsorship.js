// static/js/sponsorship.js — Sponsorship module (Input / Data / Dashboard)
let sponsorshipPerusahaan = [];

function sponsorshipLoadLookups() {
  const search = document.getElementById("sp-in-cat1-search");
  if (!search) return;  // not on the Input page
  apiFetch("/sponsorship/api/lookups").then(function (r) { return r.json(); }).then(function (data) {
    sponsorshipPerusahaan = data.perusahaan || [];
    const datalist = document.getElementById("sp-lembaga-datalist");
    (data.lembaga || []).forEach(function (name) {
      const opt = document.createElement("option");
      opt.value = name;
      datalist.appendChild(opt);
    });
  });
}

function _sponsorshipRenderCat1Results(matches) {
  const box = document.getElementById("sp-in-cat1-results");
  box.innerHTML = "";
  if (matches.length === 0) {
    box.innerHTML = '<div class="sp-autocomplete-empty">Tidak ditemukan</div>';
  } else {
    matches.forEach(function (p) {
      const item = document.createElement("div");
      item.className = "sp-autocomplete-item";
      item.textContent = p.cat1 + " (" + p.cat3 + ")";
      item.onclick = function () { _sponsorshipSelectCat1(p); };
      box.appendChild(item);
    });
  }
  box.classList.add("open");
}

function _sponsorshipSelectCat1(p) {
  document.getElementById("sp-in-cat1").value = p.cat1;
  document.getElementById("sp-in-cat1-search").value = p.cat1;
  document.getElementById("sp-in-cat2").value = p.cat2;
  document.getElementById("sp-in-cat3").value = p.cat3;
  document.getElementById("sp-in-cat1-results").classList.remove("open");
}

function sponsorshipInputSubmit() {
  const cat1 = document.getElementById("sp-in-cat1").value;
  if (!cat1) { showToast("Pilih Cat1 (Perusahaan) dari daftar.", "error"); return; }
  const payload = {
    cat: document.getElementById("sp-in-cat").value,
    description: document.getElementById("sp-in-description").value,
    cat1: cat1,
    cat4: document.getElementById("sp-in-cat4").value,
    lembaga_perorangan: document.getElementById("sp-in-lembaga").value,
    tanggal_form_sponsor: document.getElementById("sp-in-tanggal-form").value,
    tanggal_payment: document.getElementById("sp-in-tanggal-payment").value,
    perihal: document.getElementById("sp-in-perihal").value,
    amount_request: document.getElementById("sp-in-amount").value,
    reff: document.getElementById("sp-in-reff").value,
    status: document.getElementById("sp-in-status").value,
    coa: document.getElementById("sp-in-coa").value,
    cc_total: document.getElementById("sp-in-cc-total").value,
    cc: document.getElementById("sp-in-cc").value,
    source: document.getElementById("sp-in-source").value,
  };
  showLoading("Menyimpan transaksi Sponsorship...");
  apiFetch("/sponsorship/input/create", { method: "POST", body: JSON.stringify(payload) })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      showToast(data.pesan, data.ok ? "success" : "error");
      if (data.ok) { setTimeout(function () { window.location.href = "/sponsorship/data"; }, 1000); }
    })
    .catch(function () { showToast("Gagal menyimpan transaksi.", "error"); })
    .finally(function () { hideLoading(); });
}

function sponsorshipDataEdit(id) {
  showLoading("Memuat transaksi...");
  apiFetch("/sponsorship/data/" + id).then(function (r) { return r.json(); }).then(function (data) {
    if (!data.ok) { showToast(data.pesan, "error"); return; }
    const t = data.transaksi;
    document.getElementById("sp-ed-id").value = t.id;
    document.getElementById("sp-ed-perihal").value = t.perihal || "";
    document.getElementById("sp-ed-amount").value = t.amount_request;
    document.getElementById("sp-ed-tanggal-payment").value = t.tanggal_payment || "";
    document.getElementById("sp-ed-reff").value = t.reff || "";
    document.getElementById("sp-ed-status").value = t.status || "";
    document.getElementById("sp-ed-coa").value = t.coa || "";
    document.getElementById("sp-ed-cc-total").value = t.cc_total || "";
    document.getElementById("sp-ed-cc").value = t.cc || "";
    document.getElementById("sp-ed-source").value = t.source || "";
    openModal("sp-edit-modal");
  }).catch(function () {
    showToast("Gagal memuat transaksi.", "error");
  }).finally(function () {
    hideLoading();
  });
}

function sponsorshipDataSave() {
  const id = document.getElementById("sp-ed-id").value;
  const payload = {
    perihal: document.getElementById("sp-ed-perihal").value,
    amount_request: document.getElementById("sp-ed-amount").value,
    tanggal_payment: document.getElementById("sp-ed-tanggal-payment").value,
    reff: document.getElementById("sp-ed-reff").value,
    status: document.getElementById("sp-ed-status").value,
    coa: document.getElementById("sp-ed-coa").value,
    cc_total: document.getElementById("sp-ed-cc-total").value,
    cc: document.getElementById("sp-ed-cc").value,
    source: document.getElementById("sp-ed-source").value,
  };
  showLoading("Memperbarui transaksi...");
  apiFetch("/sponsorship/data/" + id + "/update", { method: "POST", body: JSON.stringify(payload) })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      showToast(data.pesan, data.ok ? "success" : "error");
      if (data.ok) { closeModal("sp-edit-modal"); setTimeout(function () { window.location.reload(); }, 1000); }
    })
    .catch(function () { showToast("Gagal memperbarui transaksi.", "error"); })
    .finally(function () { hideLoading(); });
}

document.addEventListener("DOMContentLoaded", function () {
  sponsorshipLoadLookups();
  const search = document.getElementById("sp-in-cat1-search");
  if (search) {
    search.addEventListener("input", function () {
      const q = search.value.trim().toLowerCase();
      document.getElementById("sp-in-cat1").value = "";
      document.getElementById("sp-in-cat2").value = "";
      document.getElementById("sp-in-cat3").value = "";
      if (!q) { document.getElementById("sp-in-cat1-results").classList.remove("open"); return; }
      const matches = sponsorshipPerusahaan.filter(function (p) {
        return p.cat1.toLowerCase().indexOf(q) !== -1;
      });
      _sponsorshipRenderCat1Results(matches);
    });
  }
});

let sponsorshipCharts = {};

function _sponsorshipFormatRupiah(n) {
  return "Rp " + Number(n || 0).toLocaleString("id-ID");
}

function _sponsorshipRenderSummary(summary) {
  const el = document.getElementById("sp-summary");
  const cards = [
    ["Total Amount", _sponsorshipFormatRupiah(summary.total_amount)],
    ["Jumlah Transaksi", summary.total_count],
  ];
  el.innerHTML = cards.map(function (c) {
    return '<div class="budget-stat-card"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
  }).join("");
}

function _sponsorshipRenderBarChart(canvasId, labels, values) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (sponsorshipCharts[canvasId]) sponsorshipCharts[canvasId].destroy();
  sponsorshipCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: [{ label: "Amount", data: values, backgroundColor: "#2D6ADF" }] },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });
}

function sponsorshipLoadDashboard() {
  const summaryEl = document.getElementById("sp-summary");
  if (!summaryEl) return;  // not on the Dashboard page
  const params = new URLSearchParams();
  document.querySelectorAll(".sp-dash-filter").forEach(function (el) {
    if (el.value) params.set(el.dataset.param, el.value);
  });
  apiFetch("/sponsorship/api/dashboard-data?" + params.toString())
    .then(function (r) { return r.json(); })
    .then(function (data) {
      _sponsorshipRenderSummary(data.summary);
      _sponsorshipRenderBarChart("sp-chart-monthly",
        data.monthlyChart.map(function (r) { return r.month; }),
        data.monthlyChart.map(function (r) { return r.amount; }));
      _sponsorshipRenderBarChart("sp-chart-pillar",
        data.pillarChart.map(function (r) { return r.pillar; }),
        data.pillarChart.map(function (r) { return r.amount; }));
      _sponsorshipRenderBarChart("sp-chart-description",
        data.descriptionChart.map(function (r) { return r.description; }),
        data.descriptionChart.map(function (r) { return r.amount; }));
    });
}

document.addEventListener("DOMContentLoaded", function () {
  sponsorshipLoadDashboard();
  document.querySelectorAll(".sp-dash-filter").forEach(function (el) {
    el.addEventListener("change", sponsorshipLoadDashboard);
  });
});
