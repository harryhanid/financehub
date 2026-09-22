import sys

def patch_file(filepath, func_name, color_func, formatter_func):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # The exact function I generated earlier
    old_func = f"""function {func_name}(canvasId, labels, budgets, realisasis) {{
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if ({'setfCharts' if 'sahabat' in filepath else 'dashCharts'}[canvasId]) {'setfCharts' if 'sahabat' in filepath else 'dashCharts'}[canvasId].destroy();
  
  const budgetColor = "rgba(148, 163, 184, 0.8)"; // Slate 400
  const realisasiColor = "rgba(59, 130, 246, 0.9)"; // Blue 500
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#e2e8f0" : "#475569";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

  {'setfCharts' if 'sahabat' in filepath else 'dashCharts'}[canvasId] = new Chart(ctx, {{
    type: "bar",
    data: {{
      labels: labels,
      datasets: [
        {{
          label: "Budget",
          data: budgets,
          backgroundColor: budgetColor,
          borderRadius: 4,
        }},
        {{
          label: "Realisasi",
          data: realisasis,
          backgroundColor: realisasiColor,
          borderRadius: 4,
        }}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      interaction: {{
        mode: 'index',
        intersect: false,
      }},
"""
    
    old_func_part2 = f"""      plugins: {{
        legend: {{ position: "top", labels: {{ color: textColor }} }},
        datalabels: {{
          display: false // hide data labels because bars can be crowded
        }},
        tooltip: {{
          callbacks: {{
            label: function(context) {{
              return context.dataset.label + ": " + formatRupiahShort(context.raw);
            }}
          }}
        }}
      }},
      scales: {{
        y: {{
          beginAtZero: true,
          grid: {{ color: gridColor }},
          ticks: {{
            color: textColor,
            callback: function(value) {{ return formatRupiahShort(value); }}
          }}
        }},
        x: {{
          grid: {{ display: false }},
          ticks: {{ color: textColor }}
        }}
      }}
    }}
  }});
}}
"""

    # Wait, the event handler in sahabat is slightly different:
    if 'sahabat' in filepath:
        old_func_part1 = old_func + """      onClick: function (evt, elements) {
        if (!elements.length) return;
        let lbl = labels[elements[0].index];
        if (lbl !== "Total") {
            setfSetKategoriDrilldown(lbl);
        }
      },
"""
    else:
        old_func_part1 = old_func

    full_old_func = old_func_part1 + old_func_part2

    new_func = f"""function {func_name}(canvasId, labels, budgets, realisasis) {{
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if ({'setfCharts' if 'sahabat' in filepath else 'dashCharts'}[canvasId]) {'setfCharts' if 'sahabat' in filepath else 'dashCharts'}[canvasId].destroy();
  
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#e2e8f0" : "#475569";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";
  const percentColor = isDark ? "#fbbf24" : "#d97706"; // Amber

  const budgetColors = labels.map(l => l === "Total" ? (isDark ? "#475569" : "#94a3b8") : {color_func}(l) + "66");
  const realisasiColors = labels.map(l => l === "Total" ? (isDark ? "#3b82f6" : "#2563eb") : {color_func}(l));

  {'setfCharts' if 'sahabat' in filepath else 'dashCharts'}[canvasId] = new Chart(ctx, {{
    type: "bar",
    data: {{
      labels: labels,
      datasets: [
        {{
          label: "Budget",
          data: budgets,
          backgroundColor: budgetColors,
          borderRadius: 4,
        }},
        {{
          label: "Realisasi",
          data: realisasis,
          backgroundColor: realisasiColors,
          borderRadius: 4,
        }}
      ]
    }},
    plugins: [ChartDataLabels],
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      layout: {{ padding: {{ top: 35 }} }},
      interaction: {{
        mode: 'index',
        intersect: false,
      }},
"""
    
    if 'sahabat' in filepath:
        new_func += """      onClick: function (evt, elements) {
        if (!elements.length) return;
        let lbl = labels[elements[0].index];
        if (lbl !== "Total") {
            setfSetKategoriDrilldown(lbl);
        }
      },
"""

    new_func += f"""      plugins: {{
        legend: {{ position: "top", labels: {{ color: textColor }} }},
        datalabels: {{
          display: true,
          labels: {{
            nominal: {{
              align: 'end',
              anchor: 'end',
              color: textColor,
              font: {{ size: 10, weight: '500' }},
              offset: function(context) {{
                 if (context.datasetIndex === 1 && context.chart.data.datasets[0].data[context.dataIndex] > 0) {{
                     return 12; // push up if percentage is shown
                 }}
                 return 0;
              }},
              formatter: function(value) {{
                return value ? {formatter_func}(value) : "";
              }}
            }},
            percent: {{
              align: 'end',
              anchor: 'end',
              color: percentColor,
              font: {{ size: 10, weight: 'bold' }},
              offset: -4,
              formatter: function(value, context) {{
                if (context.datasetIndex === 1) {{
                  let budgetVal = context.chart.data.datasets[0].data[context.dataIndex];
                  if (budgetVal > 0) {{
                    let pct = (value / budgetVal) * 100;
                    return '(' + pct.toFixed(1) + '%)';
                  }}
                }}
                return "";
              }}
            }}
          }}
        }},
        tooltip: {{
          callbacks: {{
            label: function(context) {{
              return context.dataset.label + ": " + {formatter_func}(context.raw);
            }}
          }}
        }}
      }},
      scales: {{
        y: {{
          beginAtZero: true,
          grid: {{ color: gridColor }},
          ticks: {{
            color: textColor,
            callback: function(value) {{ return {formatter_func}(value); }}
          }}
        }},
        x: {{
          grid: {{ display: false }},
          ticks: {{ color: textColor }}
        }}
      }}
    }}
  }});
}}
"""
    if full_old_func in content:
        content = content.replace(full_old_func, new_func)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {filepath} successfully!")
    else:
        print(f"Could not find function in {filepath}")

if __name__ == '__main__':
    patch_file(r'C:\Financehub\app\static\js\sahabat_etf.js', 'setfRenderBudgetVsRealisasiChart', 'setfColorForCategory', 'setfFmtJutaan')
    patch_file(r'C:\Financehub\app\static\js\dashboard_beasiswa.js', 'dashRenderBudgetVsRealisasiChart', 'dashColorForCategory', 'dashFmtJutaan')
