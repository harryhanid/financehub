import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix the fetch block for family_summary
fetch_target = r"""        const kesBudget = \[\];
          const kesActual = \[\];
          const penBudget = \[\];
          const penActual = \[\];

          data\.families\.forEach\(function\(f\) \{
             let kb = 0, ka = 0, pb = 0, pa = 0;
             f\.members\.forEach\(function\(m\) \{
                 if \(m\.kategori && m\.kategori\.includes\("By Medical"\)\) \{
                     kb \+= m\.budget \|\| 0;
                     ka \+= m\.realisasi \|\| 0;
                 \} else \{
                     pb \+= m\.budget \|\| 0;
                     pa \+= m\.realisasi \|\| 0;
                 \}
             \}\);
             kesBudget\.push\(kb\);
             kesActual\.push\(ka\);
             penBudget\.push\(pb\);
             penActual\.push\(pa\);
          \}\);

          const stackData = \[
              \{ name: "By Medical", budget: kesBudget, realisasi: kesActual \},
              \{ name: "By Pendidikan", budget: penBudget, realisasi: penActual \}
          \];

          setfRenderStackedGroupedChart\("chart-keluarga", xLabels, stackData, "all"\);"""

fetch_replacement = """        window._setfLastKeluargaData = data.families;
        setfRenderKeluargaChart(data.families);"""
content = re.sub(fetch_target, fetch_replacement, content)

# 2. Add event listener setup inside initSahabatETF
init_target = r"""    const reportYearSelect = document\.getElementById\("setf-report-year"\);
    if \(reportYearSelect\) \{
      reportYearSelect\.addEventListener\("change", setfUpdateReportExportLink\);"""

init_replacement = """    const reportYearSelect = document.getElementById("setf-report-year");
    if (reportYearSelect) {
      reportYearSelect.addEventListener("change", setfUpdateReportExportLink);

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
    });"""
content = re.sub(init_target, init_replacement, content)

# 3. Remove the redundant listener binding from setfRenderYearlyChart
bound_target = r"""    if \(!window\._setfYearlyChartBound\) \{
        const togglesKat = document\.querySelectorAll\("input\[name='setf-tahunan-kat-mode'\]"\);
        togglesKat\.forEach\(r => \{
            r\.addEventListener\('change', function\(\) \{
                if \(window\._setfLastYearlyData\) setfRenderTahunanKategori\(window\._setfLastYearlyData\);
            \}\);
        \}\);
        const togglesPil = document\.querySelectorAll\("input\[name='setf-tahunan-pil-mode'\]"\);
        togglesPil\.forEach\(r => \{
            r\.addEventListener\('change', function\(\) \{
                if \(window\._setfLastYearlyData\) setfRenderTahunanPillar\(window\._setfLastYearlyData\);
            \}\);
        \}\);
        const togglesKel = document\.querySelectorAll\("input\[name='setf-keluarga-mode'\]"\);
        togglesKel\.forEach\(r => \{
            r\.addEventListener\('change', function\(\) \{
                if \(window\._setfLastKeluargaData\) setfRenderKeluargaChart\(window\._setfLastKeluargaData\);
            \}\);
        \}\);
        window\._setfYearlyChartBound = true;
    \}
    """
content = re.sub(bound_target, "", content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
