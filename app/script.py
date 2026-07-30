import re

file_path = r'C:\Financehub\app\templates\payment_memo\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Insert the new JS functions just before the SML section
sml_marker = '// ── SML ───────────────────────────────────────────────────────────────────────'
js_code = '''// ── GENERIC ETF LINE EXPANSION ────────────────────────────────────────────────
function _toggleEtfExpandGeneric(event, tr, pamId, colSpan, prefix) {
  if (event.target.tagName === 'INPUT' || event.target.tagName === 'BUTTON' || event.target.tagName === 'A') return;
  const existing = document.querySelectorAll(.-detail-rows[data-pam-id=""]);
  if (existing.length) {
    const nowHidden = existing[0].style.display === 'none';
    existing.forEach(r => { r.style.display = nowHidden ? '' : 'none'; });
    return;
  }
  etfFetchDetailLines(tr, pamId, colSpan, prefix);
}

async function etfFetchDetailLines(masterTr, pamId, colSpan, prefix) {
  if (window[_LinesCache] && window[_LinesCache][pamId] === 'loading') return;
  if (!window[_LinesCache]) window[_LinesCache] = {};
  window[_LinesCache][pamId] = 'loading';

  const loadingTr = document.createElement('tr');
  loadingTr.classList.add(${prefix}-detail-rows);
  loadingTr.dataset.pamId = pamId;
  loadingTr.innerHTML = <td colspan="" style="padding:8px 36px;font-size:11px;color:#94a3b8;">Memuat detail...</td>;
  masterTr.insertAdjacentElement('afterend', loadingTr);

  const res = await apiFetch(/payment-memo/pam//beasiswa-lines);
  loadingTr.remove();

  if (!res) {
    window[_LinesCache][pamId] = null;
    const errTr = document.createElement('tr');
    errTr.classList.add(${prefix}-detail-rows);
    errTr.dataset.pamId = pamId;
    errTr.innerHTML = <td colspan="" style="padding:8px 36px;font-size:11px;color:#ef4444;background:#fff5f5;">Gagal memuat detail.</td>;
    masterTr.insertAdjacentElement('afterend', errTr);
    return;
  }
  const data = await res.json();
  if (!data.ok) {
    window[_LinesCache][pamId] = null;
    const errTr = document.createElement('tr');
    errTr.classList.add(${prefix}-detail-rows);
    errTr.dataset.pamId = pamId;
    errTr.innerHTML = <td colspan="" style="padding:8px 36px;font-size:11px;color:#ef4444;background:#fff5f5;"></td>;
    masterTr.insertAdjacentElement('afterend', errTr);
    return;
  }

  window[_LinesCache][pamId] = data.rows;
  if (!data.rows.length) {
    const emptyTr = document.createElement('tr');
    emptyTr.classList.add(${prefix}-detail-rows);
    emptyTr.dataset.pamId = pamId;
    emptyTr.innerHTML = <td colspan="" style="padding:8px 36px;font-size:11px;color:#64748b;background:#f8fafc;font-style:italic">Tidak ada detail baris (atau bukan beasiswa).</td>;
    masterTr.insertAdjacentElement('afterend', emptyTr);
    return;
  }

  let html = 
    <tr class="-detail-rows" data-pam-id="" style="background:#f1f5f9;border-bottom:2px solid #cbd5e1">
      <td colspan="" style="padding:10px 40px">
        <div style="background:#fff;border:1px solid #cbd5e1;border-radius:6px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
          <table style="width:100%;border-collapse:collapse;font-size:11px">
            <thead>
              <tr style="background:#e2e8f0;color:#334155">
                <th style="padding:6px;text-align:left">Kode</th>
                <th style="padding:6px;text-align:left">Nama / Keterangan</th>
                <th style="padding:6px;text-align:left">Kategori</th>
                <th style="padding:6px;text-align:right">Amount</th>
                <th style="padding:6px;text-align:left">Tgl Pengajuan</th>
                <th style="padding:6px;text-align:left">Tgl Receive</th>
                <th style="padding:6px;text-align:left">Tgl PA</th>
                <th style="padding:6px;text-align:left">Tgl Final</th>
              </tr>
            </thead>
            <tbody>
  ;
  data.rows.forEach(r => {
    html += \\
      <tr style="border-bottom:1px solid #e2e8f0">
        <td style="padding:6px;font-family:monospace">\\</td>
        <td style="padding:6px;font-weight:600">\\</td>
        <td style="padding:6px;color:#64748b">\\\\</td>
        <td style="padding:6px;text-align:right;font-weight:700;color:#1a56db">\\</td>
        <td style="padding:6px">\\</td>
        <td style="padding:6px">\\</td>
        <td style="padding:6px">\\</td>
        <td style="padding:6px">\\</td>
      </tr>
    \\;
  });
  html += \\
            </tbody>
          </table>
        </div>
      </td>
    </tr>
  \\;
  masterTr.insertAdjacentHTML('afterend', html);
}

'''
if js_code not in content:
    content = content.replace(sml_marker, js_code + sml_marker)

# 2. Update sml_row (LAND)
sml_target = '''<tr style="background:;">
      <td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap"></td>'''
sml_replace = '''<tr class="sml-row" style="background:;cursor:pointer" onclick="_toggleEtfExpandGeneric(event, this, , 25, 'sml')">
      <td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap">
        <span style="display:inline-block;margin-right:4px;color:#3b82f6">&#9658;</span>
      </td>'''
content = content.replace(sml_target, sml_replace)

# 3. Update setf_row (SETF)
setf_target = '''<tr style="background:;">
      <td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap"></td>'''
setf_replace = '''<tr class="setf-row" style="background:;cursor:pointer" onclick="_toggleEtfExpandGeneric(event, this, , 16, 'setf')">
      <td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap">
        <span style="display:inline-block;margin-right:4px;color:#3b82f6">&#9658;</span>
      </td>'''
content = content.replace(setf_target, setf_replace)

# 4. Update fiori_row (APP)
fiori_target = '''<tr class="fiori-row" style="background:;">
      <td class="f0" style="padding:6px 8px;text-align:center;background:"><input type="checkbox" class="fiori-cb" data-id="" style="cursor:pointer;vertical-align:middle" onchange="fioriToggleCb(this)"></td>'''
fiori_replace = '''<tr class="fiori-row" style="background:;cursor:pointer" onclick="_toggleEtfExpandGeneric(event, this, , 26, 'fiori')">
      <td class="f0" style="padding:6px 8px;text-align:center;background:"><input type="checkbox" class="fiori-cb" data-id="" style="cursor:pointer;vertical-align:middle" onchange="fioriToggleCb(this)"></td>'''
content = content.replace(fiori_target, fiori_replace)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done!")
