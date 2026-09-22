import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add setfRenderBudgetVsRealisasiChart
func = """
function setfRenderBudgetVsRealisasiChart(canvasId, labels, budgets, realisasis, onClickCallback) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (setfCharts[canvasId]) setfCharts[canvasId].destroy();

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#475569";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

    const datasets = [
        {
            label: "Budget",
            data: budgets,
            backgroundColor: "#94a3b8",
            borderColor: "#64748b",
            borderWidth: 1,
            barPercentage: 0.8,
            categoryPercentage: 0.9,
        },
        {
            label: "Realisasi",
            data: realisasis,
            backgroundColor: labels.map(l => setfColorForCategory(l)),
            borderColor: labels.map(l => setfShadeColor(setfColorForCategory(l), -25)),
            borderWidth: 2,
            barPercentage: 0.8,
            categoryPercentage: 0.9,
        }
    ];

    setfCharts[canvasId] = new Chart(ctx, {
        type: "bar",
        data: { labels: labels, datasets: datasets },
        plugins: [ChartDataLabels],
        options: {
            responsive: true,
            onClick: function (evt, elements) {
                if (!elements.length || !onClickCallback) return;
                onClickCallback(labels[elements[0].index]);
            },
            layout: { padding: { top: 20 } },
            plugins: {
                legend: { display: false },
                datalabels: {
                    anchor: "end",
                    align: "top",
                    color: textColor,
                    font: { size: 10, weight: "bold" },
                    formatter: function(val) { return val > 0 ? setfFmtJutaan(val) : ""; }
                }
            },
            scales: {
                x: {
                    ticks: { color: textColor },
                    grid: { display: false }
                },
                y: {
                    ticks: { color: textColor, callback: function (value) { return setfFmtJutaan(value); } },
                    grid: { color: gridColor }
                }
            }
        }
    });
}
"""

if "function setfRenderBudgetVsRealisasiChart" not in content:
    content += func

# Update breakdown logic
old_breakdown = """      .then(function (data) {
        setfRenderDoughnutChart("chart-kategori",
          data.kategori.map(function (k) { return k.cat1; }),
          data.kategori.map(function (k) { return k.realisasi; }),
          data.kategori.map(function (k) { return setfColorForCategory(k.cat1); }));
        setfRenderKategoriTable(data.kategori);
        setfRenderAlert(data.over_budget);
        setfRenderYearlyChart(data.yearly);
        setfRenderPillarTable(data.pillar);
      })"""

new_breakdown = """      .then(function (data) {
        setfRenderBudgetVsRealisasiChart("chart-kategori",
          data.kategori.map(function (k) { return k.cat1; }),
          data.kategori.map(function (k) { return k.budget; }),
          data.kategori.map(function (k) { return k.realisasi; }),
          setfSetKategoriDrilldown
        );
        setfRenderKategoriTable(data.kategori);
        
        if (data.pillar) {
            setfRenderBudgetVsRealisasiChart("chart-pillar",
              data.pillar.map(function (p) { return p.pillar; }),
              data.pillar.map(function (p) { return p.budget; }),
              data.pillar.map(function (p) { return p.realisasi; })
            );
        }
        
        setfRenderAlert(data.over_budget);
        setfRenderYearlyChart(data.yearly);
        setfRenderPillarTable(data.pillar);
      })"""

content = content.replace(old_breakdown, new_breakdown)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
