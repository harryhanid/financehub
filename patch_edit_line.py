import sys

def patch():
    with open(r'C:\Financehub\app\templates\payment_memo\index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    target = '<td colspan="12" style="padding:4px 8px;vertical-align:middle"></td>'
    replacement = '<td colspan="12" style="padding:4px 8px;vertical-align:middle;text-align:right"><button class="btn btn-sm" style="padding:2px 8px;font-size:10px" onclick="openEditLineModal(${r.id}, ${pamId}, \'${esc(r.nama || r.siswa_code || \'\')}\', ${r.amount})">Edit</button></td>'
    
    content = content.replace(target, replacement)

    js_logic = """
function openEditLineModal(lineId, pamId, nama, amount) {
  document.getElementById('edit-line-id').value = lineId;
  document.getElementById('edit-line-pam-id').value = pamId;
  document.getElementById('edit-line-siswa-name').value = nama;
  document.getElementById('edit-line-amount').value = amount ? parseInt(amount, 10).toLocaleString('en-US') : '0';
  openModal('modal-edit-beasiswa-line');
}

async function submitEditBeasiswaLine() {
  const lineId = parseInt(document.getElementById('edit-line-id').value);
  const pamId = parseInt(document.getElementById('edit-line-pam-id').value);
  const amount = parseFloat(document.getElementById('edit-line-amount').value.replace(/,/g, '')) || 0;
  
  const res = await apiFetch('/payment-memo/beasiswa-line/' + lineId + '/amount', {
    method: 'POST',
    body: JSON.stringify({ amount })
  });
  if (!res) return;
  const data = await res.json();
  showToast(data.pesan, data.ok ? 'success' : 'error');
  if (data.ok) {
    closeModal('modal-edit-beasiswa-line');
    
    // Invalidate the cache for this PAM so the lines reload
    if (typeof _setfBeasiswaCache !== 'undefined') _setfBeasiswaCache[pamId] = null;
    if (typeof _smlBeasiswaCache !== 'undefined') _smlBeasiswaCache[pamId] = null;
    if (typeof _energyBeasiswaCache !== 'undefined') _energyBeasiswaCache[pamId] = null;
    if (typeof _smtBeasiswaCache !== 'undefined') _smtBeasiswaCache[pamId] = null;
    if (typeof _fioriBeasiswaCache !== 'undefined') _fioriBeasiswaCache[pamId] = null;
    if (typeof _agriBeasiswaCache !== 'undefined') _agriBeasiswaCache[pamId] = null;
    
    // Refresh the table views
    if (typeof loadSETFDebounced === 'function') loadSETFDebounced();
    if (typeof loadSMLDebounced === 'function') loadSMLDebounced();
    if (typeof loadEnergyDebounced === 'function') loadEnergyDebounced();
    if (typeof loadSMTDebounced === 'function') loadSMTDebounced();
    if (typeof loadFioriDebounced === 'function') loadFioriDebounced();
    if (typeof loadAGRIDebounced === 'function') loadAGRIDebounced();
  }
}
"""
    
    # inject the javascript logic at the end of the script block
    content = content.replace('// ── Init ────────────────────────────────────────────────────────────────────────', js_logic + '\n// ── Init ────────────────────────────────────────────────────────────────────────')

    with open(r'C:\Financehub\app\templates\payment_memo\index.html', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch()
