import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix showActual
target_actual = r'let showActual = \(mode === "all" \|\| mode === "actual"\);'
replacement_actual = 'let showActual = (mode === "all" || mode === "actual" || mode === "realisasi");'
content = re.sub(target_actual, replacement_actual, content)

# Add event listeners and global data
target_yearly = r'function setfRenderYearlyChart\(yearly\) \{.*?\n      // We get mode from toggles'
replacement_yearly = """function setfRenderYearlyChart(yearly) {
      window._setfLastYearlyData = yearly;
      if (!window._setfYearlyChartBound) {
          const modeToggles = document.querySelectorAll("input[name='setf-tahunan-kat-mode'], input[name='setf-tahunan-pil-mode']");
          modeToggles.forEach(r => {
             r.addEventListener('change', function() {
                 if (window._setfLastYearlyData) {
                     setfRenderYearlyChart(window._setfLastYearlyData);
                 }
             });
          });
          window._setfYearlyChartBound = true;
      }
      // We get mode from toggles"""
content = re.sub(target_yearly, replacement_yearly, content, count=1, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
