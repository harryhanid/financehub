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

function _sponsorshipFormatJutaan(n) {
  const jt = Math.round((n || 0) / 1000000);
  return "Rp " + jt.toLocaleString("id-ID");
}

function _sponsorshipThemeColor(varName, fallback) {
  const page = document.querySelector(".budget-page");
  const val = page ? getComputedStyle(page).getPropertyValue(varName).trim() : "";
  return val || fallback;
}

function _sponsorshipRenderSummary(summary, topLembaga) {
  const el = document.getElementById("sp-summary");
  const top5Sum = (topLembaga || []).reduce(function (s, r) { return s + r.amount; }, 0);
  const concentrationPct = summary.total_amount > 0 ? (top5Sum / summary.total_amount * 100) : 0;
  const cards = [
    ["Total Amount", _sponsorshipFormatJutaan(summary.total_amount)],
    ["Jumlah Transaksi", summary.total_count],
    ["Konsentrasi Top 5", concentrationPct.toFixed(1) + "%"],
  ];
  el.innerHTML = cards.map(function (c) {
    return '<div class="sp-dash-stat-card"><div class="label">' + c[0] +
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
    plugins: [ChartDataLabels],
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        datalabels: {
          anchor: "end",
          align: "top",
          color: _sponsorshipThemeColor("--text", "#334155"),
          font: { size: 10, weight: "600" },
          formatter: v => _sponsorshipFormatJutaan(v),
        },
      },
    },
  });
}

function _sponsorshipRenderDoughnutChart(canvasId, labels, values, colors) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (sponsorshipCharts[canvasId]) sponsorshipCharts[canvasId].destroy();
  sponsorshipCharts[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors }] },
    plugins: [ChartDataLabels],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "right", labels: { color: _sponsorshipThemeColor("--text", "#334155") } },
        datalabels: {
          anchor: "center",
          align: "center",
          color: "#fff",
          font: { size: 11, weight: "600" },
          formatter: (value, ctx) => {
            const total = ctx.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
            return total > 0 ? (value / total * 100).toFixed(1) + "%" : "";
          },
        },
      }
    }
  });
}

function _sponsorshipCollectFilters() {
  const tahun = Array.from(document.querySelectorAll(".sp-dash-tahun-cb:checked")).map(function (cb) { return cb.value; });
  const cat = Array.from(document.querySelectorAll(".sp-dash-cat-cb:checked")).map(function (cb) { return cb.value; });
  const cat3 = Array.from(document.querySelectorAll(".sp-dash-pillar-cb:checked")).map(function (cb) { return cb.value; });
  const cat4Select = document.querySelector('.sp-dash-filter[data-param="cat4"]');
  return { tahun: tahun, cat: cat, cat3: cat3, cat4: cat4Select ? cat4Select.value : "" };
}

function _sponsorshipBuildParams(filters) {
  const params = new URLSearchParams();
  filters.tahun.forEach(function (v) { params.append("tahun", v); });
  filters.cat.forEach(function (v) { params.append("cat", v); });
  filters.cat3.forEach(function (v) { params.append("cat3", v); });
  if (filters.cat4) params.set("cat4", filters.cat4);
  return params;
}

function _sponsorshipUpdateChipSummary(chip) {
  const boxes = chip.querySelectorAll(".panel-opts input[type=checkbox]");
  const total = boxes.length;
  const checked = chip.querySelectorAll(".panel-opts input[type=checkbox]:checked").length;
  const valEl = chip.querySelector(".val");
  if (checked === total) {
    valEl.textContent = "Semua";
  } else if (checked === 0) {
    valEl.textContent = "Tidak ada";
  } else {
    valEl.textContent = checked + " dipilih";
  }
}

function _sponsorshipInitFilterChips() {
  document.querySelectorAll(".sp-dash-filter-chip").forEach(function (chip) {
    chip.querySelectorAll(".panel-opts input[type=checkbox]").forEach(function (cb) {
      cb.addEventListener("change", function () {
        _sponsorshipUpdateChipSummary(chip);
        sponsorshipLoadDashboard();
      });
    });
    const allBtn = chip.querySelector('[data-act="all"]');
    if (allBtn) {
      allBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        chip.querySelectorAll(".panel-opts input[type=checkbox]").forEach(function (cb) { cb.checked = true; });
        _sponsorshipUpdateChipSummary(chip);
        sponsorshipLoadDashboard();
      });
    }
    const noneBtn = chip.querySelector('[data-act="none"]');
    if (noneBtn) {
      noneBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        chip.querySelectorAll(".panel-opts input[type=checkbox]").forEach(function (cb) { cb.checked = false; });
        _sponsorshipUpdateChipSummary(chip);
        sponsorshipLoadDashboard();
      });
    }
    chip.addEventListener("click", function (e) {
      if (e.target.closest(".sp-dash-filter-panel")) return;
      document.querySelectorAll(".sp-dash-filter-chip.open").forEach(function (c) {
        if (c !== chip) c.classList.remove("open");
      });
      chip.classList.toggle("open");
    });
    _sponsorshipUpdateChipSummary(chip);
  });

  document.addEventListener("click", function (e) {
    if (!e.target.closest(".sp-dash-filter-chip")) {
      document.querySelectorAll(".sp-dash-filter-chip.open").forEach(function (c) { c.classList.remove("open"); });
    }
  });
}

function _sponsorshipRenderYoyGrowth(yoyRows) {
  const tbody = document.querySelector("#sp-table-yoy tbody");
  if (!tbody) return;
  if (!yoyRows.length) {
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted)">Belum ada data.</td></tr>';
    return;
  }
  let html = "";
  yoyRows.forEach(function (r) {
    let growthCell = "–";
    if (r.growth_pct !== null) {
      const cls = r.growth_pct >= 0 ? "sp-dash-growth-positive" : "sp-dash-growth-negative";
      const sign = r.growth_pct >= 0 ? "+" : "";
      growthCell = '<span class="' + cls + '">' + sign + r.growth_pct.toFixed(1) + "%</span>";
    }
    html += "<tr><td>" + r.year + '</td><td class="num-right">' + _sponsorshipFormatJutaan(r.amount) +
      '</td><td class="num-right">' + growthCell + "</td></tr>";
  });
  tbody.innerHTML = html;
}

function sponsorshipLoadDashboard() {
  const summaryEl = document.getElementById("sp-summary");
  if (!summaryEl) return;
  const filters = _sponsorshipCollectFilters();
  const params = _sponsorshipBuildParams(filters);
  apiFetch("/sponsorship/api/dashboard-data?" + params.toString())
    .then(function (r) { return r.json(); })
    .then(function (data) {
      _sponsorshipRenderSummary(data.summary, data.topLembaga);
      _sponsorshipRenderBarChart("sp-chart-monthly", data.monthlyChart.map(x=>x.month), data.monthlyChart.map(x=>x.amount));
      _sponsorshipRenderBarChart("sp-chart-description", data.descriptionChart.map(x=>x.description), data.descriptionChart.map(x=>x.amount));
      _sponsorshipRenderYoyGrowth(data.yoyGrowth);

      // Render Pillar Scorecards
      const spScorecards = document.getElementById("sp-scorecards");
      if (spScorecards && data.pillarSummaryTable) {
        let scHtml = "";
        const pTint = {
          "APP": "tint-app",
          "ENERGY & FINANCE": "tint-energy",
          "PROPERTY": "tint-property",
          "AGRI": "tint-agri"
        };
        const pLabels = {
          "APP": "APP",
          "ENERGY & FINANCE": "ENERGY",
          "PROPERTY": "PROPERTY",
          "AGRI": "AGRI"
        };
        const renderOrder = ["APP", "ENERGY & FINANCE", "PROPERTY", "AGRI"];

        renderOrder.forEach(pil => {
          const row = data.pillarSummaryTable.find(r => r.pillar === pil);
          if (row) {
            scHtml += `
            <div class="sp-dash-stat-card ${pTint[pil]}">
              <div class="label">${pLabels[pil]}</div>
              <div class="value">${row.pct.toFixed(2)}%</div>
              <div class="sub">${_sponsorshipFormatJutaan(row.amount)}</div>
            </div>`;
          }
        });
        spScorecards.innerHTML = scHtml;
      }

      // Render Top 5 Lembaga
      if (document.getElementById("sp-table-lembaga") && data.topLembaga) {
        let tpHtml = "";
        data.topLembaga.forEach(r => {
          tpHtml += `<tr>
            <td>${_sponsorshipEsc(r.lembaga)}</td>
            <td class="num-right">${_sponsorshipFormatJutaan(r.amount)}</td>
          </tr>`;
        });
        document.querySelector("#sp-table-lembaga tbody").innerHTML = tpHtml;
      }

      // Render Status Chart
      if (data.statusChart) {
        _sponsorshipRenderDoughnutChart(
          "sp-chart-status",
          data.statusChart.map(x => x.status),
          data.statusChart.map(x => x.amount),
          ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#64748b"]
        );
      }

      // Render Cat Mix Chart
      if (data.catMix) {
        _sponsorshipRenderDoughnutChart(
          "sp-chart-catmix",
          data.catMix.map(x => x.cat),
          data.catMix.map(x => x.amount),
          ["#2D6ADF", "#f59e0b"]
        );
      }

      // Render Cat4 Mix Chart
      if (data.cat4Mix) {
        _sponsorshipRenderDoughnutChart(
          "sp-chart-cat4mix",
          data.cat4Mix.map(x => x.cat4),
          data.cat4Mix.map(x => x.amount),
          ["#10b981", "#ef4444"]
        );
      }

      // Render Desc vs Pillar
      let dpHtml = "";
      data.descPillarTable.forEach(r => {
        dpHtml += `<tr>
          <td>${r.description}</td>
          <td class="num-right" style="font-weight:600">${_sponsorshipFormatJutaan(r.total)}</td>
          <td class="num-right">${_sponsorshipFormatJutaan(r["APP"])}</td>
          <td class="num-right">${_sponsorshipFormatJutaan(r["ENERGY & FINANCE"])}</td>
          <td class="num-right">${_sponsorshipFormatJutaan(r["PROPERTY"])}</td>
          <td class="num-right">${_sponsorshipFormatJutaan(r["AGRI"])}</td>
        </tr>`;
      });
      document.querySelector("#sp-table-desc-pillar tbody").innerHTML = dpHtml;

      // Render Desc vs Year
      let dyThead = `<tr><th>Description</th><th class="num-right">Grand Total</th>`;
      data.sortedYears.forEach(y => {
        dyThead += `<th class="num-right">${y}</th>`;
      });
      dyThead += `</tr>`;
      document.getElementById("sp-thead-desc-year").innerHTML = dyThead;

      let dyHtml = "";
      data.descYearTable.forEach(r => {
        dyHtml += `<tr>
          <td>${r.description}</td>
          <td class="num-right" style="font-weight:600">${_sponsorshipFormatJutaan(r.total)}</td>`;
        data.sortedYears.forEach(y => {
          dyHtml += `<td class="num-right">${_sponsorshipFormatJutaan(r[y])}</td>`;
        });
        dyHtml += `</tr>`;
      });
      document.querySelector("#sp-table-desc-year tbody").innerHTML = dyHtml;

      // Render grouped bar chart Year vs Pillar
      const ctxYP = document.getElementById("sp-chart-year-pillar");
      if (ctxYP) {
        if (sponsorshipCharts["sp-chart-year-pillar"]) sponsorshipCharts["sp-chart-year-pillar"].destroy();
        const pilColors = {
          "APP": "#fca5a5",
          "ENERGY & FINANCE": "#86efac",
          "PROPERTY": "#c4b5fd",
          "AGRI": "#fdba74"
        };
        const datasets = ["APP", "ENERGY & FINANCE", "PROPERTY", "AGRI"].map(pil => {
          return {
            label: pil,
            data: data.sortedYears.map(y => data.yearPillarChart[y] ? data.yearPillarChart[y][pil] : 0),
            backgroundColor: pilColors[pil] || "#ccc"
          };
        });

        sponsorshipCharts["sp-chart-year-pillar"] = new Chart(ctxYP, {
          type: "bar",
          data: { labels: data.sortedYears, datasets: datasets },
          plugins: [ChartDataLabels],
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: "top", labels: { color: _sponsorshipThemeColor("--text", "#334155") } },
              datalabels: {
                anchor: "end",
                align: "top",
                color: _sponsorshipThemeColor("--text", "#334155"),
                font: { size: 9, weight: "600" },
                formatter: v => v > 0 ? _sponsorshipFormatJutaan(v) : "",
              },
            },
            scales: {
              x: { ticks: { color: _sponsorshipThemeColor("--text-muted", "#64748b") } },
              y: { ticks: { color: _sponsorshipThemeColor("--text-muted", "#64748b"), callback: v => (v/1000000).toFixed(0) + "M" } }
            }
          }
        });
      }

    })
    .catch(function () {
      if(window.showToast) showToast("Gagal memuat data dashboard.", "error");
    });
}

document.addEventListener("DOMContentLoaded", function () {
  _sponsorshipInitFilterChips();
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

const _SP_REPORT_PILLAR_COLS = ["app_amount", "energy_finance_amount", "property_amount", "agri_amount"];
const _SP_REPORT_PILLAR_LABELS = ["APP", "ENERGY", "PROPERTY", "AGRI"];

let sponsorshipReportState = { cat4: "include", tahun: "" };

  function _getReportTahun() {
    const cbs = document.querySelectorAll("#sp-report-tahun input[name='tahun']:checked");
    return Array.from(cbs).map(cb => cb.value);
  }

  function sponsorshipLoadReport() {
    const container = document.getElementById("sp-report-table-container");
    if (!container) return;  // not on the Report page
    
    const tahuns = _getReportTahun();
    if ((!sponsorshipReportState.tahun || sponsorshipReportState.tahun.length === 0) && tahuns.length > 0) {
      sponsorshipReportState.tahun = tahuns;
    }
    
    const params = new URLSearchParams();
    params.append("cat4", sponsorshipReportState.cat4);
    const selectedTahun = sponsorshipReportState.tahun || [];
    const tahunArr = Array.isArray(selectedTahun) ? selectedTahun : [selectedTahun];
    tahunArr.forEach(t => params.append("tahun", t));

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

    const refreshBtn = document.getElementById("sp-report-refresh");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function() {
        sponsorshipReportState.tahun = _getReportTahun();
        sponsorshipLoadReport();
      });
    }

    const exportBtn = document.getElementById("sp-report-export");
    if (exportBtn) {
      exportBtn.addEventListener("click", function () {
        sponsorshipReportState.tahun = _getReportTahun();
        const params = new URLSearchParams();
        params.append("cat4", sponsorshipReportState.cat4);
        const selectedTahun = sponsorshipReportState.tahun || [];
        const tahunArr = Array.isArray(selectedTahun) ? selectedTahun : [selectedTahun];
        tahunArr.forEach(t => params.append("tahun", t));
        window.location.href = "/sponsorship/report/export?" + params.toString();
      });
    }

  sponsorshipLoadReport();
});
