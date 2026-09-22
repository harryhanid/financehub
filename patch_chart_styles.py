import sys
import re

def patch_js(filepath, func_name, color_func, formatter_func):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the function body to replace
    pattern = r'(function ' + func_name + r'\(canvasId, labels, budgets, realisasis\) \{.*?\}\s*\})'
    
    new_func = f"""function {func_name}(canvasId, labels, budgets, realisasis) {{
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  
  // Use a global or specific chart store depending on the file
  let chartStore = typeof setfCharts !== "undefined" ? setfCharts : dashCharts;
  if (chartStore[canvasId]) chartStore[canvasId].destroy();
  
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#e2e8f0" : "#475569";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";
  const percentColor = isDark ? "#fbbf24" : "#d97706"; // Amber color to differentiate

  // Dynamic colors matching category table
  const budgetColors = labels.map(l => l === "Total" ? (isDark ? "#475569" : "#94a3b8") : {color_func}(l) + "66");
  const realisasiColors = labels.map(l => l === "Total" ? (isDark ? "#3b82f6" : "#2563eb") : {color_func}(l));

  chartStore[canvasId] = new Chart(ctx, {{
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
      onClick: function (evt, elements) {{
        if (!elements.length) return;
        let lbl = labels[elements[0].index];
        if (lbl !== "Total") {{
            if (typeof setfSetKategoriDrilldown === "function") setfSetKategoriDrilldown(lbl);
        }}
      }},
      plugins: {{
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
}}"""

    # We will replace the entire function body
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content.replace(match.group(1), new_func)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {filepath} successfully!")
    else:
        print(f"Could not find function {func_name} in {filepath}")

if __name__ == '__main__':
    patch_js(r'C:\Financehub\app\static\js\sahabat_etf.js', 'setfRenderBudgetVsRealisasiChart', 'setfColorForCategory', 'setfFmtJutaan')
    patch_js(r'C:\Financehub\app\static\js\dashboard_beasiswa.js', 'dashRenderBudgetVsRealisasiChart', 'dashColorForCategory', 'dashFmtJutaan')
