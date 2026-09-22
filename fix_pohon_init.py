import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target1 = r'if \(btn.dataset.subtab === "detail" && !window._setfDetailLoaded\) \{\s*window._setfDetailLoaded = true;\s*setfLoadDetailTransaksi\(\);\s*\}'
replacement1 = """if (btn.dataset.subtab === "detail" && !window._setfDetailLoaded) {
          window._setfDetailLoaded = true;
          setfLoadDetailTransaksi();
        }
        if (btn.dataset.subtab === "pohon" && !window._setfPohonLoaded) {
          window._setfPohonLoaded = true;
          setfLoadPohon();
        }"""
content = re.sub(target1, replacement1, content)

target2 = r'initFilterChips\(document\.getElementById\("setf-subtab-detail"\), setfLoadDetailTransaksi\);'
replacement2 = """initFilterChips(document.getElementById("setf-subtab-detail"), setfLoadDetailTransaksi);
    initFilterChips(document.getElementById("setf-subtab-pohon"), setfLoadPohon);
    
    const pohonYearSelect = document.getElementById("setf-pohon-year");
    if (pohonYearSelect) {
      pohonYearSelect.addEventListener("change", function () {
        if (window._setfPohonLoaded) setfLoadPohon();
      });
    }"""
content = re.sub(target2, replacement2, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
