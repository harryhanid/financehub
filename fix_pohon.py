import re

with open('app/static/js/sahabat_etf.js', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Update initSetfSubtabs
old_subtabs = """      if (btn.dataset.subtab === "laporan" && !window._setfLaporanLoaded) {
        window._setfLaporanLoaded = true;
        setfLoadLaporan();
      }
      if (btn.dataset.subtab === "detail" && !window._setfDetailLoaded) {
        window._setfDetailLoaded = true;
        setfLoadDetailTransaksi();
      }"""

new_subtabs = """      if (btn.dataset.subtab === "laporan" && !window._setfLaporanLoaded) {
        window._setfLaporanLoaded = true;
        setfLoadLaporan();
      }
      if (btn.dataset.subtab === "detail" && !window._setfDetailLoaded) {
        window._setfDetailLoaded = true;
        setfLoadDetailTransaksi();
      }
      if (btn.dataset.subtab === "pohon" && !window._setfPohonLoaded) {
        window._setfPohonLoaded = true;
        setfLoadPohon();
      }"""
c = c.replace(old_subtabs, new_subtabs)

# 2. Update initSahabatEtf
old_init = """  const laporanTab = document.getElementById("setf-subtab-laporan");
  if (laporanTab) {
    initFilterChips(laporanTab, reloadLaporan);
  }"""

new_init = """  const laporanTab = document.getElementById("setf-subtab-laporan");
  if (laporanTab) {
    initFilterChips(laporanTab, reloadLaporan);
  }
  
  const pohonTab = document.getElementById("setf-subtab-pohon");
  if (pohonTab) {
    initFilterChips(pohonTab, function() {
      if (window._setfPohonLoaded) setfLoadPohon();
    });
  }
  const reportPohonMonth = document.getElementById("setf-pohon-month");
  if (reportPohonMonth) {
    reportPohonMonth.addEventListener("change", function() {
      if (window._setfPohonLoaded) setfLoadPohon();
    });
  }"""
c = c.replace(old_init, new_init)

with open('app/static/js/sahabat_etf.js', 'w', encoding='utf-8') as f:
    f.write(c)

print("Pohon wired up!")
