import re

file_path = "C:/Financehub/app/templates/sahabat_etf/_panel.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'<div class="budget-chart-card"><h3>Budget vs Actual per Sahabat</h3><canvas id="chart-keluarga"></canvas></div>'
replacement = """<div class="budget-chart-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
              <h3 style="margin: 0;">Budget vs Actual per Sahabat</h3>
              <div class="chart-toggle-group">
                <label><input type="radio" name="setf-keluarga-mode" value="all" checked> All</label>
                <label><input type="radio" name="setf-keluarga-mode" value="budget"> Budget</label>
                <label><input type="radio" name="setf-keluarga-mode" value="realisasi"> Actual</label>
              </div>
            </div>
            <div style="height: 350px;"><canvas id="chart-keluarga"></canvas></div>
          </div>"""

content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
