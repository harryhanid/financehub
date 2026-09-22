import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'    const reportYearSelect = document\.getElementById\("setf-report-year"\);\s*if \(reportYearSelect\) \{\s*reportYearSelect\.addEventListener\("change", setfUpdateReportExportLink\);\s*reportYearSelect\.addEventListener\("change", function \(\) \{\s*if \(window\._setfLaporanLoaded\) setfLoadLaporan\(\);\s*\}\);\s*setfUpdateReportExportLink\(\);\s*\}\s*setfApplyFilters\(\);\s*\}'

replacement = """    const reportYearSelect = document.getElementById("setf-report-year");
    if (reportYearSelect) {
      reportYearSelect.addEventListener("change", setfUpdateReportExportLink);
      reportYearSelect.addEventListener("change", function () {
        if (window._setfLaporanLoaded) setfLoadLaporan();
      });
      setfUpdateReportExportLink();
    }
    
    // Bind chart toggles
    document.querySelectorAll("input[name='setf-tahunan-kat-mode']").forEach(r => {
        r.addEventListener('change', function() {
            if (window._setfLastYearlyData) setfRenderTahunanKategori(window._setfLastYearlyData);
        });
    });
    document.querySelectorAll("input[name='setf-tahunan-pil-mode']").forEach(r => {
        r.addEventListener('change', function() {
            if (window._setfLastYearlyData) setfRenderTahunanPillar(window._setfLastYearlyData);
        });
    });
    document.querySelectorAll("input[name='setf-keluarga-mode']").forEach(r => {
        r.addEventListener('change', function() {
            if (window._setfLastKeluargaData) setfRenderKeluargaChart(window._setfLastKeluargaData);
        });
    });

    setfApplyFilters();
  }"""

content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
