import re

with open('app/static/js/sahabat_etf.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update setfUpdateReportExportLink
new_export = """function setfUpdateReportExportLink() {
  const sel = document.getElementById("setf-report-year");
  const link = document.getElementById("setf-export-report");
  if (!sel || !link) return;
  
  let qs = "year=" + encodeURIComponent(sel.value);
  const monthSel = document.getElementById("setf-report-month");
  if (monthSel) qs += "&month=" + encodeURIComponent(monthSel.value);
  
  const pillars = Array.from(document.querySelectorAll(".setf-laporan-pillar-cb:checked")).map(function (cb) { return cb.value; });
  pillars.forEach(function (p) { qs += "&pillars[]=" + encodeURIComponent(p); });
  
  link.href = "/beasiswa/sahabat/export/report?" + qs;
}"""
content = re.sub(
    r'function setfUpdateReportExportLink\(\) \{[\s\S]*?\}',
    new_export,
    content,
    count=1
)

# 2. Update setfLoadLaporan
new_load = """function setfLoadLaporan() {
  const sel = document.getElementById('setf-report-year');
  if (!sel) return;
  
  let qs = 'year=' + encodeURIComponent(sel.value);
  const monthSel = document.getElementById('setf-report-month');
  if (monthSel) qs += '&month=' + encodeURIComponent(monthSel.value);
  
  const pillars = Array.from(document.querySelectorAll('.setf-laporan-pillar-cb:checked')).map(function (cb) { return cb.value; });
  pillars.forEach(function (p) { qs += '&pillars[]=' + encodeURIComponent(p); });

  document.getElementById('setf-laporan-content').innerHTML =
    '<p style="color:var(--text-muted);text-align:center;padding:2rem">Memuat laporan...</p>';
  fetch('/beasiswa/sahabat/api/report?' + qs)
    .then(function (r) { return r.json(); })
    .then(function (resp) {
      if (!resp.ok) { showToast(resp.pesan || 'Gagal memuat laporan.', 'error'); return; }
      setfRenderLaporan(resp.data);
    })
    .catch(function () { showToast('Gagal memuat laporan.', 'error'); });
}"""
content = re.sub(
    r'function setfLoadLaporan\(\) \{[\s\S]*?\}',
    new_load,
    content,
    count=1
)

# 3. Update initSahabatEtf
old_init = """  const reportYearSelect = document.getElementById("setf-report-year");
  if (reportYearSelect) {
    reportYearSelect.addEventListener("change", setfUpdateReportExportLink);
    reportYearSelect.addEventListener("change", function () {
      if (window._setfLaporanLoaded) setfLoadLaporan();
    });
    setfUpdateReportExportLink();
  }"""
  
new_init = """  const reportYearSelect = document.getElementById("setf-report-year");
  const reportMonthSelect = document.getElementById("setf-report-month");
  
  function reloadLaporan() {
    setfUpdateReportExportLink();
    if (window._setfLaporanLoaded) setfLoadLaporan();
  }
  
  if (reportYearSelect) {
    reportYearSelect.addEventListener("change", reloadLaporan);
    setfUpdateReportExportLink();
  }
  if (reportMonthSelect) {
    reportMonthSelect.addEventListener("change", reloadLaporan);
  }
  
  const laporanTab = document.getElementById("setf-subtab-laporan");
  if (laporanTab) {
    initFilterChips(laporanTab, reloadLaporan);
  }"""
content = content.replace(old_init, new_init)

with open('app/static/js/sahabat_etf.js', 'w', encoding='utf-8') as f:
    f.write(content)
