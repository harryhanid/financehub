import sys
import re

def patch_file(filepath, formatter_func):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add plugins: [ChartDataLabels]
    content = re.sub(
        r'(\btype:\s*"bar",\s*data:\s*\{.*?\},)(\s*options:\s*\{)',
        r'\1\n    plugins: [ChartDataLabels],\2',
        content,
        flags=re.DOTALL
    )

    # 2. Update datalabels config
    old_datalabels = """datalabels: {
          display: false // hide data labels because bars can be crowded
        },"""
    new_datalabels = f"""datalabels: {{
          display: true,
          align: 'end',
          anchor: 'end',
          color: textColor,
          font: {{ size: 10, weight: '500' }},
          textAlign: 'center',
          formatter: function(value, context) {{
            if (!value) return "";
            let label = {formatter_func}(value);
            // If it's the Realisasi dataset (index 1), add percentage
            if (context.datasetIndex === 1) {{
              let budgetVal = context.chart.data.datasets[0].data[context.dataIndex];
              if (budgetVal > 0) {{
                let pct = (value / budgetVal) * 100;
                label += '\\n(' + pct.toFixed(1) + '%)';
              }}
            }}
            return label;
          }}
        }},"""
    
    # 3. Increase top padding so labels aren't cut off
    old_layout = "options: {"
    new_layout = """options: {
      layout: { padding: { top: 30 } },"""

    if "layout: { padding:" not in content:
        content = content.replace(old_layout, new_layout)
        
    content = content.replace(old_datalabels, new_datalabels)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch_file(r'C:\Financehub\app\static\js\sahabat_etf.js', 'setfFmtJutaan')
    patch_file(r'C:\Financehub\app\static\js\dashboard_beasiswa.js', 'dashFmtJutaan')
    print("Patched both files successfully!")
