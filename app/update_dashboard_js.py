path = r"C:\Financehub\app\static\js\sponsorship.js"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

import re

# Add scorecards rendering
new_logic = """
      // Render Pillar Scorecards
      const spScorecards = document.getElementById("sp-scorecards");
      if (spScorecards && data.pillarSummaryTable) {
        let scHtml = "";
        const pColors = {
          "APP": "#fca5a5",
          "ENERGY & FINANCE": "#86efac",
          "PROPERTY": "#c4b5fd",
          "AGRI": "#fdba74"
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
            <div class="sp-scorecard">
              <div class="sp-scorecard-indicator" style="background-color: ${pColors[pil]}"></div>
              <div class="sp-scorecard-title">${pLabels[pil]}</div>
              <div class="sp-scorecard-amount">${_sponsorshipFormatRupiah(row.amount)}</div>
              <div class="sp-scorecard-pct" style="color: ${pColors[pil]}">${row.pct.toFixed(2)}% Allocation</div>
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
            <td class="num-right">${_sponsorshipFormatRupiah(r.amount)}</td>
          </tr>`;
        });
        document.querySelector("#sp-table-lembaga tbody").innerHTML = tpHtml;
      }

      // Render Status Chart
      const ctxStatus = document.getElementById("sp-chart-status");
      if (ctxStatus && data.statusChart) {
        if (sponsorshipCharts["sp-chart-status"]) sponsorshipCharts["sp-chart-status"].destroy();
        const sLabels = data.statusChart.map(x => x.status);
        const sData = data.statusChart.map(x => x.amount);
        sponsorshipCharts["sp-chart-status"] = new Chart(ctxStatus, {
          type: "doughnut",
          data: {
            labels: sLabels,
            datasets: [{
              data: sData,
              backgroundColor: ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#64748b"]
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: "right", labels: {color: "#cbd5e1"} }
            }
          }
        });
      }
"""

c = c.replace(
    '// Render Desc vs Pillar',
    new_logic + '\n      // Render Desc vs Pillar'
)

# Fix dataset order in grouped bar chart Year vs Pillar to match APP, ENERGY, PROPERTY, AGRI
c = c.replace(
    'const datasets = ["AGRI", "APP", "ENERGY & FINANCE", "PROPERTY"].map(pil => {',
    'const datasets = ["APP", "ENERGY & FINANCE", "PROPERTY", "AGRI"].map(pil => {'
)

# Update _sponsorshipFormatRupiah and _sponsorshipRenderSummary if needed (already fine)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done sponsorship.js")
