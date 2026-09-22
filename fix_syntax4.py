file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

import re

target = re.search(r'setfCharts\[canvasId\] = new Chart\(ctx, \{\s*type: "bar",\s*data: \{ labels: xLabels, datasets: datasets \},\s*plugins: \[ChartDataLabels, customKeluargaLabelsPlugin\],[\s\S]*?\}\s*\}\s*\);\s*\}', content)

if target:
    print("Found broken chart!")
    start_idx = target.start()
    
    replacement = """function setfRenderStackedBarChart(canvasId, families) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#e2e8f0" : "#475569";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

  const maxMembers = families.reduce(function (m, f) { return Math.max(m, f.members.length); }, 0);
  const datasets = [];
  const shapes = ['dot', 'diagonal-right-left', 'square', 'zigzag', 'triangle', 'weave', 'cross'];
  
  for (let i = 0; i < maxMembers; i++) {
    const color = SETF_PALETTE[i % SETF_PALETTE.length];
    const shape = shapes[i % shapes.length];
    datasets.push({
      label: "Anggota " + (i + 1) + " (Budget)",
      data: families.map(function (f) { return i < f.members.length ? f.members[i].budget : null; }),
      backgroundColor: color,
      borderColor: setfShadeColor(color, -20),
      borderWidth: 1,
      stack: "StackBudget",
      barPercentage: 0.8,
      categoryPercentage: 0.8
    });
    datasets.push({
      label: "Anggota " + (i + 1) + " (Actual)",
      data: families.map(function (f) { return i < f.members.length ? f.members[i].realisasi : null; }),
      backgroundColor: typeof pattern !== 'undefined' ? pattern.draw(shape, color) : color,
      borderColor: setfShadeColor(color, -20),
      borderWidth: 1,
      stack: "StackRealisasi",
      barPercentage: 0.8,
      categoryPercentage: 0.8
    });
  }

  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: families.map(function (f) { return f.label; }), datasets: datasets },
    plugins: [ChartDataLabels, setfStackTotalPlugin],
    options: {
      responsive: true,
      layout: { padding: { top: 20, bottom: 25 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (item) {
              const memberIdx = Math.floor(item.datasetIndex / 2);
              const isBudget = (item.datasetIndex % 2) === 0;
              const member = families[item.dataIndex].members[memberIdx];
              if (!member) return "";
              const val = isBudget ? member.budget : member.realisasi;
              return member.nama + (isBudget ? " (Budget)" : "") + ": " + setfFmtJutaan(val);
            },
          },
        },
        datalabels: {
          display: false
        }
      },
      scales: {
        x: { 
            stacked: true, 
            ticks: { color: isDark ? "#94a3b8" : "#64748b", padding: 20 }, 
            grid: { color: isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)", display: false } 
        },
        y: {
          stacked: true,
          ticks: {
            color: isDark ? "#94a3b8" : "#64748b",
            callback: function (value) { return setfFmtJutaan(value); },
          },
          grid: { color: isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)" },
        },
      },
    }
  });
}"""

    # We replace from the dangling setfCharts[canvasId] down to the end of the broken syntax block
    # Actually, the regex matches until the end of the broken syntax!
    new_content = content[:start_idx] + replacement + content[target.end():]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Fixed!")
else:
    print("Could not find broken chart!")
