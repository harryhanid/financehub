// static/js/sponsorship.js — Sponsorship module (Input / Data / Dashboard)
let sponsorshipPerusahaan = [];

function sponsorshipLoadLookups() {
  const inputSearch = document.getElementById("sp-in-cat1-search");
  const editSearch = document.getElementById("sp-ed-cat1-search");
  if (!inputSearch && !editSearch) return;
  apiFetch("/sponsorship/api/lookups").then(function (r) { return r.json(); }).then(function (data) {
    sponsorshipPerusahaan = data.perusahaan || [];
    const datalist = document.getElementById("sp-lembaga-datalist");
    if (datalist) {
      (data.lembaga || []).forEach(function (name) {
        const opt = document.createElement("option");
        opt.value = name;
        datalist.appendChild(opt);
      });
    }
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

function _sponsorshipRenderCat1ResultsEdit(matches) {
  const box = document.getElementById("sp-ed-cat1-results");
  box.innerHTML = "";
  if (matches.length === 0) {
    box.innerHTML = '<div class="sp-autocomplete-empty">Tidak ditemukan</div>';
  } else {
    matches.forEach(function (p) {
      const item = document.createElement("div");
      item.className = "sp-autocomplete-item";
      item.textContent = p.cat1 + " (" + p.cat3 + ")";
      item.onclick = function () { _sponsorshipSelectCat1Edit(p); };
      box.appendChild(item);
    });
  }
  box.classList.add("open");
}

function _sponsorshipSelectCat1Edit(p) {
  document.getElementById("sp-ed-cat1").value = p.cat1;
  document.getElementById("sp-ed-cat1-search").value = p.cat1;
  document.getElementById("sp-ed-cat2").value = p.cat2;
  document.getElementById("sp-ed-cat3").value = p.cat3;
  document.getElementById("sp-ed-cat1-results").classList.remove("open");
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

function _sponsorshipEnsureSelectHasValue(selectId, value) {
  const el = document.getElementById(selectId);
  el.value = value;
  if (el.value !== value && value) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = value + " (nilai lama, tidak ada di daftar)";
    el.appendChild(opt);
    el.value = value;
  }
}

function sponsorshipDataEdit(id) {
  showLoading("Memuat transaksi...");
  apiFetch("/sponsorship/data/" + id).then(function (r) { return r.json(); }).then(function (data) {
    if (!data.ok) { showToast(data.pesan, "error"); return; }
    const t = data.transaksi;
    document.getElementById("sp-ed-id").value = t.id;
    document.getElementById("sp-ed-cat").value = t.cat;
    _sponsorshipEnsureSelectHasValue("sp-ed-description", t.description);
    document.getElementById("sp-ed-cat1").value = t.cat1;
    document.getElementById("sp-ed-cat1-search").value = t.cat1;
    document.getElementById("sp-ed-cat2").value = t.cat2;
    document.getElementById("sp-ed-cat3").value = t.cat3;
    _sponsorshipEnsureSelectHasValue("sp-ed-cat4", t.cat4 || "");
    document.getElementById("sp-ed-lembaga").value = t.lembaga_perorangan;
    document.getElementById("sp-ed-tanggal-form").value = t.tanggal_form_sponsor;
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
    cat: document.getElementById("sp-ed-cat").value,
    description: document.getElementById("sp-ed-description").value,
    cat1: document.getElementById("sp-ed-cat1").value,
    cat4: document.getElementById("sp-ed-cat4").value,
    lembaga_perorangan: document.getElementById("sp-ed-lembaga").value,
    tanggal_form_sponsor: document.getElementById("sp-ed-tanggal-form").value,
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
  const editSearch = document.getElementById("sp-ed-cat1-search");
  if (editSearch) {
    editSearch.addEventListener("input", function () {
      const q = editSearch.value.trim().toLowerCase();
      document.getElementById("sp-ed-cat1").value = "";
      document.getElementById("sp-ed-cat2").value = "";
      document.getElementById("sp-ed-cat3").value = "";
      if (!q) { document.getElementById("sp-ed-cat1-results").classList.remove("open"); return; }
      const matches = sponsorshipPerusahaan.filter(function (p) {
        return p.cat1.toLowerCase().indexOf(q) !== -1;
      });
      _sponsorshipRenderCat1ResultsEdit(matches);
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

// ── Report tab ──────────────────────────────────────────────────────────
function _sponsorshipEsc(s) {
  const d = document.createElement("div");
  d.textContent = String(s ?? "");
  return d.innerHTML;
}

const _SP_REPORT_PILLAR_COLS = ["app_amount", "agri_amount", "energy_finance_amount", "property_amount"];
const _SP_REPORT_PILLAR_LABELS = ["APP", "AGRI", "ENERGY & FINANCE", "PROPERTY"];

let sponsorshipReportState = { cat4: "include", tahun: "" };

function sponsorshipLoadReport() {
  const container = document.getElementById("sp-report-table-container");
  if (!container) return;  // not on the Report page
  const tahunSelect = document.getElementById("sp-report-tahun");
  if (!sponsorshipReportState.tahun && tahunSelect) sponsorshipReportState.tahun = tahunSelect.value;
  const params = new URLSearchParams({ tahun: sponsorshipReportState.tahun, cat4: sponsorshipReportState.cat4 });
  apiFetch("/sponsorship/api/report-data?" + params.toString())
    .then(function (r) { return r.json(); })
    .then(function (data) { _sponsorshipRenderReportTable(container, data); })
    .catch(function () {
      container.innerHTML = '<div class="budget-card"><p>Gagal memuat data report.</p></div>';
    });
}

function _sponsorshipRenderReportTable(container, data) {
  if (!data.sections || data.sections.length === 0) {
    container.innerHTML = '<div class="budget-card"><p>Belum ada data sponsorship untuk tahun ' +
      _sponsorshipEsc(data.tahun) + '.</p></div>';
    return;
  }
  let html = '<table class="budget-table sp-report-table">';
  data.sections.forEach(function (section) {
    html += '<thead><tr><th>NO</th><th>LEMBAGA / PERORANGAN</th><th>PERIHAL</th>' +
      _SP_REPORT_PILLAR_LABELS.map(function (l) { return "<th>" + l + "</th>"; }).join("") +
      '<th>TOTAL</th></tr></thead><tbody>';
    html += '<tr class="sp-report-section-band"><td colspan="' + (4 + _SP_REPORT_PILLAR_LABELS.length) + '">' +
      _sponsorshipEsc(section.description.toUpperCase()) + '</td></tr>';
    section.rows.forEach(function (row) {
      html += '<tr><td>' + row.no + '</td><td>' + _sponsorshipEsc(row.lembaga_perorangan) +
        '</td><td>' + _sponsorshipEsc(row.perihal || "") + '</td>' +
        _SP_REPORT_PILLAR_COLS.map(function (c) {
          return '<td class="num-right">' + (row[c] ? fmtRupiah(row[c]) : "-") + '</td>';
        }).join("") +
        '<td class="num-right">' + fmtRupiah(row.total) + '</td></tr>';
    });
    html += '<tr class="sp-report-subtotal-row"><td colspan="3">TOTAL ' +
      _sponsorshipEsc(section.description.toUpperCase()) + '</td>' +
      _SP_REPORT_PILLAR_COLS.map(function (c) {
        return '<td class="num-right">' + fmtRupiah(section.subtotal[c]) + '</td>';
      }).join("") +
      '<td class="num-right">' + fmtRupiah(section.subtotal.total) + '</td></tr>';
    html += '</tbody>';
  });
  html += '<tfoot>';
  html += '<tr class="sp-report-grandtotal-row"><td colspan="3">TOTAL SPONSORSHIP (ACTUAL)</td>' +
    _SP_REPORT_PILLAR_COLS.map(function (c) {
      return '<td class="num-right">' + fmtRupiah(data.grand_total[c]) + '</td>';
    }).join("") +
    '<td class="num-right">' + fmtRupiah(data.grand_total.total) + '</td></tr>';
  html += '<tr class="sp-report-pct-row"><td colspan="3">% Allocation</td>' +
    _SP_REPORT_PILLAR_COLS.map(function (c) { return '<td class="num-right">' + data.pct_allocation[c] + '%</td>'; }).join("") +
    '<td></td></tr>';
  html += '</tfoot></table>';
  container.innerHTML = html;
}

document.addEventListener("DOMContentLoaded", function () {
  const container = document.getElementById("sp-report-table-container");
  if (!container) return;  // not on the Report page

  document.querySelectorAll(".sp-report-cat4-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".sp-report-cat4-btn").forEach(function (b) { b.classList.remove("active"); });
      btn.classList.add("active");
      sponsorshipReportState.cat4 = btn.dataset.cat4;
      sponsorshipLoadReport();
    });
  });

  const tahunSelect = document.getElementById("sp-report-tahun");
  if (tahunSelect) {
    sponsorshipReportState.tahun = tahunSelect.value;
    tahunSelect.addEventListener("change", function () {
      sponsorshipReportState.tahun = tahunSelect.value;
      sponsorshipLoadReport();
    });
  }

  const refreshBtn = document.getElementById("sp-report-refresh");
  if (refreshBtn) refreshBtn.addEventListener("click", sponsorshipLoadReport);

  const exportBtn = document.getElementById("sp-report-export");
  if (exportBtn) {
    exportBtn.addEventListener("click", function () {
      const params = new URLSearchParams({ tahun: sponsorshipReportState.tahun, cat4: sponsorshipReportState.cat4 });
      window.location.href = "/sponsorship/report/export?" + params.toString();
    });
  }

  sponsorshipLoadReport();
});
