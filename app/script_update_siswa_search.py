path = r"C:\Financehub\app\templates\etf_payment_application\index.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

import re
pattern = re.compile(r"function setupCreateSiswaSearch\(\) \{.*?(?=\n\nfunction|\n\s*//)", re.DOTALL)

new_func = """function setupCreateSiswaSearch() {
  const searchInp = document.getElementById('pa-siswa-search');
  const idInp     = document.getElementById('pa-siswa-id');
  const codeInp   = document.getElementById('pa-siswa-code');
  const infoDiv   = document.getElementById('pa-siswa-info');
  const sugg      = document.getElementById('pa-siswa-sugg');
  if (!searchInp) return;
  let debounce;
  let activeIdx = -1;

  searchInp.addEventListener('keydown', (e) => {
    if (sugg.style.display === 'none') return;
    const items = sugg.querySelectorAll('div');
    if (!items.length) return;
    
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIdx = (activeIdx + 1) % items.length;
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIdx = (activeIdx - 1 + items.length) % items.length;
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIdx > -1 && items[activeIdx]) {
        items[activeIdx].onmousedown();
      }
      return;
    } else {
      return;
    }
    
    items.forEach((item, idx) => {
      if (idx === activeIdx) {
        item.style.backgroundColor = 'var(--accent, #5B8CFF)';
        item.style.color = '#fff';
      } else {
        item.style.backgroundColor = '';
        item.style.color = '';
      }
    });
  });

  searchInp.addEventListener('input', () => {
    activeIdx = -1;
    clearTimeout(debounce);
    const q = searchInp.value.trim();
    if (q.length < 2) { sugg.style.display = 'none'; return; }
    debounce = setTimeout(async () => {
      const resp = await apiFetch(`/etf-payment-application/siswa-search?q=${encodeURIComponent(q)}&tab=${ACTIVE_TAB}`);
      const data = await resp.json();
      sugg.innerHTML = '';
      if (!data.length) { sugg.style.display = 'none'; return; }
      data.forEach(s => {
        const item = document.createElement('div');
        item.style.cssText = 'padding:.4rem .6rem;cursor:pointer;font-size:.8rem;border-bottom:1px solid var(--border)';
        item.textContent = `${s.nama} (${s.code}) - ${s.jenjang} ${s.angkatan}`;
        item.onmousedown = () => {
          searchInp.value = s.nama;
          idInp.value     = s.id;
          codeInp.value   = s.code;
          if (infoDiv) infoDiv.textContent = `${s.universitas||''} | ${s.program||''} | ${s.fakultas||''} | Status: ${s.status}`;
          sugg.style.display = 'none';
          _etfpaIpkLoadPromise = apiFetch(`/beasiswa/siswa/${s.code}`).then(r=>r.json()).then(d=>{
            if (d.ok) _etfpaUpdateCreateIpk(d.data);
            else showToast('Gagal memuat IPK siswa - cek manual sebelum simpan.', 'error');
          }).catch(() => {
            showToast('Gagal memuat IPK siswa - cek manual sebelum simpan.', 'error');
          });
        };
        sugg.appendChild(item);
      });
      sugg.style.display = 'block';
    }, 400);
  });
  searchInp.addEventListener('blur', () => { setTimeout(() => sugg.style.display = 'none', 150); });
  searchInp.addEventListener('focus', () => { if (searchInp.value.trim().length >= 2 && sugg.innerHTML) sugg.style.display = 'block'; });
}"""

c = pattern.sub(new_func, c, count=1)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("done")
