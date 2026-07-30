import re

file_path = r'C:\Financehub\app\templates\payment_memo\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# I will find the exact block and replace it
# The block starts at `// ── GENERIC ETF LINE EXPANSION` and ends before `// ── SML`
# But the characters might have been corrupted. I'll search using regex for `// [^\n]*GENERIC ETF LINE EXPANSION[^\n]*\n.*?// [^\n]*SML[^\n]*\n`

start_marker = r'// [^\n]*GENERIC ETF LINE EXPANSION[^\n]*\n'
end_marker = r'// [^\n]*SML[^\n]*\n'

pattern = start_marker + r'.*?' + end_marker

correct_js_code = """// ── GENERIC ETF LINE EXPANSION ────────────────────────────────────────────────
function _toggleEtfExpandGeneric(event, tr, pamId, colSpan, prefix) {
  if (event.target.tagName === 'INPUT' || event.target.tagName === 'BUTTON' || event.target.tagName === 'A') return;
  const existing = document.querySelectorAll(`.${prefix}-detail-rows[data-pam-id="${pamId}"]`);
  if (existing.length) {
    const nowHidden = existing[0].style.display === 'none';
    existing.forEach(r => { r.style.display = nowHidden ? '' : 'none'; });
    return;
  }
  etfFetchDetailLines(tr, pamId, colSpan, prefix);
}

async function etfFetchDetailLines(masterTr, pamId, colSpan, prefix) {
  if (window[`_${prefix}LinesCache`] && window[`_${prefix}LinesCache`][pamId] === 'loading') return;
  if (!window[`_${prefix}LinesCache`]) window[`_${prefix}LinesCache`] = {};
  window[`_${prefix}LinesCache`][pamId] = 'loading';

  const loadingTr = document.createElement('tr');
  loadingTr.classList.add(`${prefix}-detail-rows`);
  loadingTr.dataset.pamId = pamId;
  loadingTr.innerHTML = `<td colspan="${colSpan}" style="padding:8px 36px;font-size:11px;color:#94a3b8;">Memuat detail...</td>`;
  masterTr.insertAdjacentElement('afterend', loadingTr);

  const res = await apiFetch(`/payment-memo/pam/${pamId}/beasiswa-lines`);
  loadingTr.remove();

  if (!res) {
    window[`_${prefix}LinesCache`][pamId] = null;
    const errTr = document.createElement('tr');
    errTr.classList.add(`${prefix}-detail-rows`);
    errTr.dataset.pamId = pamId;
    errTr.innerHTML = `<td colspan="${colSpan}" style="padding:8px 36px;font-size:11px;color:#ef4444;background:#fff5f5;">Gagal memuat detail.</td>`;
    masterTr.insertAdjacentElement('afterend', errTr);
    return;
  }
  const data = await res.json();
  if (!data.ok) {
    window[`_${prefix}LinesCache`][pamId] = null;
    const errTr = document.createElement('tr');
    errTr.classList.add(`${prefix}-detail-rows`);
    errTr.dataset.pamId = pamId;
    errTr.innerHTML = `<td colspan="${colSpan}" style="padding:8px 36px;font-size:11px;color:#ef4444;background:#fff5f5;">${esc(data.pesan)}</td>`;
    masterTr.insertAdjacentElement('afterend', errTr);
    return;
  }

  window[`_${prefix}LinesCache`][pamId] = data.rows;
  if (!data.rows.length) {
    const emptyTr = document.createElement('tr');
    emptyTr.classList.add(`${prefix}-detail-rows`);
    emptyTr.dataset.pamId = pamId;
    emptyTr.innerHTML = `<td colspan="${colSpan}" style="padding:8px 36px;font-size:11px;color:#64748b;background:#f8fafc;font-style:italic">Tidak ada detail baris (atau bukan beasiswa).</td>`;
    masterTr.insertAdjacentElement('afterend', emptyTr);
    return;
  }

  let html = `
    <tr class="${prefix}-detail-rows" data-pam-id="${pamId}" style="background:#f1f5f9;border-bottom:2px solid #cbd5e1">
      <td colspan="${colSpan}" style="padding:10px 40px">
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
  `;
  data.rows.forEach(r => {
    html += `
      <tr style="border-bottom:1px solid #e2e8f0">
        <td style="padding:6px;font-family:monospace">${esc(r.siswa_code || '-')}</td>
        <td style="padding:6px;font-weight:600">${esc(r.nama || '-')}</td>
        <td style="padding:6px;color:#64748b">${esc(r.cat1 || '')}${r.cat2 ? ' · ' + esc(r.cat2) : ''}</td>
        <td style="padding:6px;text-align:right;font-weight:700;color:#1a56db">${fmtRupiah(r.amount)}</td>
        <td style="padding:6px">${esc(r.tgl_pengajuan || '-')}</td>
        <td style="padding:6px">${esc(r.tgl_receive || '-')}</td>
        <td style="padding:6px">${esc(r.tgl_pa || '-')}</td>
        <td style="padding:6px">${esc(r.tgl_final || '-')}</td>
      </tr>
    `;
  });
  html += `
            </tbody>
          </table>
        </div>
      </td>
    </tr>
  `;
  masterTr.insertAdjacentHTML('afterend', html);
}

// ── SML ───────────────────────────────────────────────────────────────────────
"""

new_content, count = re.subn(pattern, correct_js_code, content, flags=re.DOTALL)
print(f"Replaced {count} times")

if count > 0:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
