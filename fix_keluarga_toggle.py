import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add event listener for radio
event_listener = """
  document.querySelectorAll('input[name="setf-keluarga-mode"]').forEach(function(el) {
    el.addEventListener("change", function() {
       if (window._setfLastKeluargaData) {
           setfRenderKeluargaChart(window._setfLastKeluargaData);
       }
    });
  });
"""
content = content.replace('document.querySelectorAll(\'input[name="setf-tahunan-pil-mode"]\').forEach(function(el) {', event_listener + '\n  document.querySelectorAll(\'input[name="setf-tahunan-pil-mode"]\').forEach(function(el) {')

# Extract setfRenderKeluargaChart logic
extract_target = r"""        const xLabels = data\.families\.map\(function \(f\) \{
          if \(f\.members\.length > 1\) \{
            return \[f\.label, f\.members\.map\(function \(m\) \{ return setfFirstName\(m\.nama\); \}\)\.join\(", "\)\];
          \}
          return setfFirstName\(f\.members\[0\]\.nama\);
        \}\);
        const kesBudget = \[\];
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

new_logic = """
        window._setfLastKeluargaData = data.families;
        setfRenderKeluargaChart(data.families);
"""
content = re.sub(extract_target, new_logic, content)

new_func = """
function setfRenderKeluargaChart(families) {
    const xLabels = families.map(function (f) {
        if (f.members.length > 1) {
            return [f.label, f.members.map(function (m) { return setfFirstName(m.nama); }).join(", ")];
        }
        return setfFirstName(f.members[0].nama);
    });
    const kesBudget = [];
    const kesActual = [];
    const penBudget = [];
    const penActual = [];

    families.forEach(function(f) {
        let kb = 0, ka = 0, pb = 0, pa = 0;
        f.members.forEach(function(m) {
            if (m.kategori && m.kategori.includes("By Medical")) {
                kb += m.budget || 0;
                ka += m.realisasi || 0;
            } else {
                pb += m.budget || 0;
                pa += m.realisasi || 0;
            }
        });
        kesBudget.push(kb);
        kesActual.push(ka);
        penBudget.push(pb);
        penActual.push(pa);
    });

    const stackData = [
        { name: "By Medical", budget: kesBudget, realisasi: kesActual },
        { name: "By Pendidikan", budget: penBudget, realisasi: penActual }
    ];

    let mode = "all";
    const selectedMode = document.querySelector('input[name="setf-keluarga-mode"]:checked');
    if (selectedMode) mode = selectedMode.value;

    setfRenderStackedGroupedChart("chart-keluarga", xLabels, stackData, mode);
}
"""

content = content + "\n" + new_func

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
