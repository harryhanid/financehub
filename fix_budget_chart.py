import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'function setfRenderBudgetVsRealisasiChart\(canvasId, labels, budgets, realisasis, onClickCallback\).*?    \}\);\n\}'

replacement = """function setfRenderBudgetVsRealisasiChart(canvasId, labels, budgets, realisasis, onClickCallback) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#475569";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

    const datasets = [
        {
            label: "Budget",
            data: budgets,
            backgroundColor: "#cbd5e1",
            borderColor: "#94a3b8",
            borderWidth: 1,
            barPercentage: 0.8,
            categoryPercentage: 0.9,
        },
        {
            label: "Realisasi",
            data: realisasis,
            backgroundColor: "#3b82f6",
            borderColor: "#2563eb",
            borderWidth: 1,
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
                legend: { 
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: { color: textColor, boxWidth: 12 }
                },
                datalabels: {
                    anchor: "end",
                    align: "top",
                    color: textColor,
                    font: { size: 10, weight: "bold" },
                    textAlign: "center",
                    formatter: function(val, context) {
                        if (val <= 0) return "";
                        let text = setfFmtJutaan(val);
                        if (context.datasetIndex === 1) { // Realisasi
                            const b = context.chart.data.datasets[0].data[context.dataIndex];
                            if (b > 0) {
                                const pct = (val / b * 100).toFixed(1);
                                text += "\\n(" + pct + "%)";
                            }
                        }
                        return text;
                    }
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
}"""

content = re.sub(target, replacement, content, count=1, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
