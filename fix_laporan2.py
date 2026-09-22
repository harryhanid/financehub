with open('app/static/js/sahabat_etf.js', 'r', encoding='utf-8') as f:
    c = f.read()

# Fix the broken setfLoadLaporan block.
# We will just replace everything from "function setfLoadLaporan() {" up to the start of "// --- Detail Transaksi tab"
start_idx = c.find('function setfLoadLaporan() {')
end_idx = c.find('// \u2500\u2500\u2500 Detail Transaksi tab:')
if end_idx == -1:
    end_idx = c.find('function setfGetDetailFilters() {')

if start_idx != -1 and end_idx != -1:
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
}

"""
    c = c[:start_idx] + new_load + c[end_idx:]

with open('app/static/js/sahabat_etf.js', 'w', encoding='utf-8') as f:
    f.write(c)
