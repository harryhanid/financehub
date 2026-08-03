path = r"C:\Financehub\app\static\js\sponsorship.js"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

import re

pattern = r"function sponsorshipLoadDashboard\(\) \{[\s\S]*?    \}\);\n\}"
match = re.search(pattern, c)

if match:
    old_func = match.group(0)
    new_func = """function sponsorshipLoadDashboard() {
  const summaryEl = document.getElementById("sp-summary");
  if (!summaryEl) return;
  const params = new URLSearchParams();
  document.querySelectorAll(".sp-dash-filter").forEach(function (el) {
    if (el.value) params.set(el.dataset.param, el.value);
  });
  apiFetch("/sponsorship/api/dashboard-data?" + params.toString())
    .then(function (r) { return r.json(); })
    .then(function (data) {
      _sponsorshipRenderSummary(data.summary);
      _sponsorshipRenderBarChart("sp-chart-monthly", data.monthlyChart.map(x=>x.month), data.monthlyChart.map(x=>x.amount));
      _sponsorshipRenderBarChart("sp-chart-pillar", data.pillarChart.map(x=>x.pillar), data.pillarChart.map(x=>x.amount));
      _sponsorshipRenderBarChart("sp-chart-description", data.descriptionChart.map(x=>x.description), data.descriptionChart.map(x=>x.amount));
      
      // Render Desc vs Pillar
      let dpHtml = "";
      data.descPillarTable.forEach(r => {
        dpHtml += `<tr>
          <td>${r.description}</td>
          <td class="num-right" style="font-weight:600">${_sponsorshipFormatRupiah(r.total)}</td>
          <td class="num-right">${_sponsorshipFormatRupiah(r["APP"])}</td>
          <td class="num-right">${_sponsorshipFormatRupiah(r["ENERGY & FINANCE"])}</td>
          <td class="num-right">${_sponsorshipFormatRupiah(r["PROPERTY"])}</td>
          <td class="num-right">${_sponsorshipFormatRupiah(r["AGRI"])}</td>
        </tr>`;
      });
      document.querySelector("#sp-table-desc-pillar tbody").innerHTML = dpHtml;
      
      // Render Pillar Summary
      let psHtml = "";
      data.pillarSummaryTable.forEach(r => {
        let isGT = r.pillar === "Grand Total";
        psHtml += `<tr ${isGT ? 'style="font-weight:600;background:#1e293b;color:white;"' : ''}>
          <td>${r.pillar}</td>
          <td class="num-right">${_sponsorshipFormatRupiah(r.amount)}</td>
          <td class="num-right">${r.pct.toFixed(2)}%</td>
        </tr>`;
      });
      document.querySelector("#sp-table-pillar-summary tbody").innerHTML = psHtml;
      
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
          <td class="num-right" style="font-weight:600">${_sponsorshipFormatRupiah(r.total)}</td>`;
        data.sortedYears.forEach(y => {
          dyHtml += `<td class="num-right">${_sponsorshipFormatRupiah(r[y])}</td>`;
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
        const datasets = ["AGRI", "APP", "ENERGY & FINANCE", "PROPERTY"].map(pil => {
          return {
            label: pil,
            data: data.sortedYears.map(y => data.yearPillarChart[y] ? data.yearPillarChart[y][pil] : 0),
            backgroundColor: pilColors[pil] || "#ccc"
          };
        });
        
        sponsorshipCharts["sp-chart-year-pillar"] = new Chart(ctxYP, {
          type: "bar",
          data: { labels: data.sortedYears, datasets: datasets },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: "top", labels: {color: "#cbd5e1"} } },
            scales: {
              x: { ticks: { color: "#cbd5e1" } },
              y: { ticks: { color: "#cbd5e1", callback: v => (v/1000000).toFixed(0) + "M" } }
            }
          }
        });
      }

    })
    .catch(function () {
      if(window.showToast) showToast("Gagal memuat data dashboard.", "error");
    });
}"""
    c = c.replace(old_func, new_func)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("done replacing sponsorshipLoadDashboard")
else:
    print("could not find sponsorshipLoadDashboard")
