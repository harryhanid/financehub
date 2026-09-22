with open('app/static/js/sahabat_etf.js', 'r', encoding='utf-8') as f:
    c = f.read()

yearly_funcs = """let setfYearlyData = null;

function setfRenderTahunanData(yearly) {
  setfYearlyData = yearly;
  setfRenderTahunanKategori();
  setfRenderTahunanPillar();
}

function setfRenderTahunanKategori() {
  const modeEl = document.querySelector('input[name="setf-tahunan-kat-mode"]:checked');
  const mode = modeEl ? modeEl.value : "all";
  const data = setfYearlyData;
  if (!data || !data.years || !data.years.length) {
    if (setfCharts["chart-tahunan-kategori"]) { setfCharts["chart-tahunan-kategori"].destroy(); delete setfCharts["chart-tahunan-kategori"]; }
    const tb = document.querySelector("#setf-tahunan-kategori-table tbody");
    if(tb) tb.innerHTML = '<tr><td colspan="2" style="text-align:center;color:var(--text-muted)">Belum ada data.</td></tr>';
    return;
  }
  
  let tbodyHtml = "";
  data.kategori.forEach(function(k) {
    const total = k.realisasi.reduce((a,b)=>a+b, 0);
    tbodyHtml += "<tr><td>" + k.name + '</td><td class="num-right">' + setfFmtJutaan(total) + "</td></tr>";
  });
  const grandTotal = data.kategori.reduce((s, k) => s + k.realisasi.reduce((a,b)=>a+b,0), 0);
  tbodyHtml += '<tr style="font-weight:bold"><td>Total</td><td class="num-right">' + setfFmtJutaan(grandTotal) + '</td></tr>';
  const tb = document.querySelector("#setf-tahunan-kategori-table tbody");
  if(tb) tb.innerHTML = tbodyHtml;

  const labels = data.years.map(y => String(y));
  const datasets = [];
  data.kategori.forEach(function(k, idx) {
    const color = SETF_PALETTE[idx % SETF_PALETTE.length];
    if (mode === "all" || mode === "budget") {
      datasets.push({ label: k.name + " (Budget)", data: k.budget, backgroundColor: color, stack: "budget" });
    }
    if (mode === "all" || mode === "realisasi") {
      datasets.push({ label: k.name + " (Actual)", data: k.realisasi, backgroundColor: setfShadeColor(color, -25), stack: "actual" });
    }
  });
  
  if (setfCharts["chart-tahunan-kategori"]) setfCharts["chart-tahunan-kategori"].destroy();
  const ctx = document.getElementById("chart-tahunan-kategori");
  if(ctx) {
    setfCharts["chart-tahunan-kategori"] = new Chart(ctx, {
      type: "bar",
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'right', labels: { color: setfThemeColor("--text-primary", "#e2e8f0") } } },
        scales: {
          x: { stacked: true, ticks: { color: setfThemeColor("--text-muted", "#94a3b8") } },
          y: { stacked: true, ticks: { callback: function (value) { return (value / 1000000).toFixed(1) + "M"; }, color: setfThemeColor("--text-muted", "#94a3b8") } }
        }
      }
    });
  }
}

function setfRenderTahunanPillar() {
  const modeEl = document.querySelector('input[name="setf-tahunan-pil-mode"]:checked');
  const mode = modeEl ? modeEl.value : "all";
  const data = setfYearlyData;
  if (!data || !data.years || !data.years.length) {
    if (setfCharts["chart-tahunan-pillar"]) { setfCharts["chart-tahunan-pillar"].destroy(); delete setfCharts["chart-tahunan-pillar"]; }
    const tb = document.querySelector("#setf-tahunan-pillar-table tbody");
    if(tb) tb.innerHTML = '<tr><td colspan="2" style="text-align:center;color:var(--text-muted)">Belum ada data.</td></tr>';
    return;
  }
  
  let tbodyHtml = "";
  data.pillar.forEach(function(k) {
    const total = k.realisasi.reduce((a,b)=>a+b, 0);
    tbodyHtml += "<tr><td>" + k.name + '</td><td class="num-right">' + setfFmtJutaan(total) + "</td></tr>";
  });
  const grandTotal = data.pillar.reduce((s, k) => s + k.realisasi.reduce((a,b)=>a+b,0), 0);
  tbodyHtml += '<tr style="font-weight:bold"><td>Total</td><td class="num-right">' + setfFmtJutaan(grandTotal) + '</td></tr>';
  const tb = document.querySelector("#setf-tahunan-pillar-table tbody");
  if(tb) tb.innerHTML = tbodyHtml;

  const labels = data.years.map(y => String(y));
  const datasets = [];
  data.pillar.forEach(function(k, idx) {
    const color = SETF_PALETTE[idx % SETF_PALETTE.length];
    if (mode === "all" || mode === "budget") {
      datasets.push({ label: k.name + " (Budget)", data: k.budget, backgroundColor: color, stack: "budget" });
    }
    if (mode === "all" || mode === "realisasi") {
      datasets.push({ label: k.name + " (Actual)", data: k.realisasi, backgroundColor: setfShadeColor(color, -25), stack: "actual" });
    }
  });
  
  if (setfCharts["chart-tahunan-pillar"]) setfCharts["chart-tahunan-pillar"].destroy();
  const ctx = document.getElementById("chart-tahunan-pillar");
  if(ctx) {
    setfCharts["chart-tahunan-pillar"] = new Chart(ctx, {
      type: "bar",
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'right', labels: { color: setfThemeColor("--text-primary", "#e2e8f0") } } },
        scales: {
          x: { stacked: true, ticks: { color: setfThemeColor("--text-muted", "#94a3b8") } },
          y: { stacked: true, ticks: { callback: function (value) { return (value / 1000000).toFixed(1) + "M"; }, color: setfThemeColor("--text-muted", "#94a3b8") } }
        }
      }
    });
  }
}

"""

old_func = """function setfRenderYearlyChart(yearly) {
  if (!yearly || !yearly.length) {
    if (setfCharts["chart-tahunan"]) { setfCharts["chart-tahunan"].destroy(); delete setfCharts["chart-tahunan"]; }
    return;
  }
  setfRenderBarChart("chart-tahunan", yearly.map(function (y) { return y.tahun; }), [
    { label: "Realisasi", data: yearly.map(function (y) { return y.realisasi; }), backgroundColor: "#10b981" },
  ]);
}"""
c = c.replace(old_func, yearly_funcs)

# Now, add skeleton initialization and listeners
init_old = """  document.querySelector("#setf-table tbody").innerHTML = skeletonRows(8, 6);
  document.querySelector("#setf-kategori-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-latest-payments-table tbody").innerHTML = skeletonRows(5, 6);
  document.querySelector("#setf-pillar-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-family-table tbody").innerHTML = skeletonRows(4, 6);"""

init_new = """  document.querySelector("#setf-table tbody").innerHTML = skeletonRows(8, 6);
  document.querySelector("#setf-kategori-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-latest-payments-table tbody").innerHTML = skeletonRows(5, 6);
  document.querySelector("#setf-pillar-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-family-table tbody").innerHTML = skeletonRows(4, 6);
  const tkat = document.querySelector("#setf-tahunan-kategori-table tbody");
  if(tkat) tkat.innerHTML = skeletonRows(3, 2);
  const tpil = document.querySelector("#setf-tahunan-pillar-table tbody");
  if(tpil) tpil.innerHTML = skeletonRows(3, 2);"""
c = c.replace(init_old, init_new)

# Fetch call replacement
old_fetch = """      setfRenderYearlyChart(data.yearly);"""
new_fetch = """      setfRenderTahunanData(data.yearly);"""
c = c.replace(old_fetch, new_fetch)

# Add event listeners on initialization
listeners_idx = c.find('document.getElementById("setf-download-report").addEventListener')
if listeners_idx != -1:
    listeners_new = """  document.querySelectorAll('input[name="setf-tahunan-kat-mode"]').forEach(function(el) {
    el.addEventListener('change', setfRenderTahunanKategori);
  });
  document.querySelectorAll('input[name="setf-tahunan-pil-mode"]').forEach(function(el) {
    el.addEventListener('change', setfRenderTahunanPillar);
  });\n\n"""
    c = c[:listeners_idx] + listeners_new + c[listeners_idx:]

with open('app/static/js/sahabat_etf.js', 'w', encoding='utf-8') as f:
    f.write(c)

print("sahabat_etf.js patched by patch_dashboard2.py successfully!")
