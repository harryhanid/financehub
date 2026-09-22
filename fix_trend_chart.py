import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

hex2rgba = """function setfHexToRgba(hex, alpha) {
    let r = parseInt(hex.slice(1, 3), 16),
        g = parseInt(hex.slice(3, 5), 16),
        b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}"""

if "function setfHexToRgba" not in content:
    content = hex2rgba + "\n\n" + content

target = r'function setfRenderStackedGroupedChart\(canvasId, years, dataList, mode\).*?        \}\n    \}\);\n\}'

replacement = """function setfRenderStackedGroupedChart(canvasId, years, dataList, mode) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#475569";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

    let activeItems = dataList;
    let datasets = [];
    let showBudget = (mode === "all" || mode === "budget");
    let showActual = (mode === "all" || mode === "actual");

    activeItems.forEach(function(item) {
       let color = setfColorForCategory(item.name);
       if (canvasId.includes("pillar")) {
           if (item.name === "AGRI") color = "#10b981";
           else if (item.name === "APP") color = "#3b82f6";
           else if (item.name === "FINANCE") color = "#f59e0b";
           else if (item.name === "SETF") color = "#8b5cf6";
           else color = "#64748b";
       }
       
       if (showBudget) {
           datasets.push({
               label: item.name + " (Budget)",
               data: item.budget,
               backgroundColor: setfHexToRgba(color, 0.3),
               borderColor: color,
               borderWidth: 1,
               stack: "StackBudget",
               barPercentage: 0.8,
               categoryPercentage: 0.8
           });
       }
       
       if (showActual) {
           datasets.push({
               label: item.name + " (Realisasi)",
               data: item.realisasi,
               backgroundColor: color,
               borderColor: setfShadeColor(color, -20),
               borderWidth: 1,
               stack: "StackRealisasi",
               barPercentage: 0.8,
               categoryPercentage: 0.8
           });
       }
    });

    setfCharts[canvasId] = new Chart(ctx, {
        type: "bar",
        data: { labels: years, datasets: datasets },
        plugins: [ChartDataLabels, setfStackTotalPlugin],
        options: {
            responsive: true,
            layout: { padding: { top: 20 } },
            plugins: {
                legend: { 
                   display: true,
                   position: 'top',
                   align: 'start',
                   labels: { color: textColor, boxWidth: 12 }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return context.dataset.label + ": " + setfFmtJutaan(context.raw);
                        }
                    }
                },
                datalabels: {
                    display: false
                }
            },
            scales: {
                x: {
                    stacked: true,
                    ticks: { color: textColor },
                    grid: { display: false }
                },
                y: {
                    stacked: true,
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
