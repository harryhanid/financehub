# SLA Tab Chip Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tampilkan chip tag per baris yang di-tick di tab SLA (Days of PAM), persisten lintas perubahan search, sehingga user selalu tahu mana saja yang sudah terpilih dalam batch update.

**Architecture:** Pure JS + HTML change di satu file (`app/templates/payment_memo/index.html`). Tambah state Map `_dopSelectionMeta` untuk menyimpan label chip (nama + cat1) agar chip bisa dirender meski barisnya sudah ter-filter keluar. Chips row `#dop-chips-row` di-render ulang setiap kali selection berubah.

**Tech Stack:** Vanilla JS (ES6 Set/Map), Jinja2 HTML template, inline CSS sesuai style guide existing codebase.

---

## File Modified

- `app/templates/payment_memo/index.html` — satu-satunya file yang diubah

---

## Task 1: Tambah HTML chips row + state `_dopSelectionMeta`

**Files:**
- Modify: `app/templates/payment_memo/index.html:265-268` (HTML — chips row div)
- Modify: `app/templates/payment_memo/index.html:1472` (JS state)

- [ ] **Step 1: Tambah div `#dop-chips-row` di HTML**

  Cari blok di sekitar line 265 (tepat setelah `</div>` penutup filter-bar, sebelum `<!-- Table -->`):

  ```html
      </div>
    </div>

    <!-- Table — secondary filters + date inputs in subheader -->
    <div style="overflow-x:auto">
  ```

  Ganti dengan:

  ```html
      </div>
    </div>

    <!-- Chip tags — selected rows persisten lintas search -->
    <div id="dop-chips-row" style="display:none;padding:5px 10px;background:#eff6ff;border-bottom:1px solid #bfdbfe;display:none;align-items:center;gap:5px;flex-wrap:wrap"></div>

    <!-- Table — secondary filters + date inputs in subheader -->
    <div style="overflow-x:auto">
  ```

  > Note: `display:none` ditulis dua kali di inline style — yang kedua override yang pertama. Ini sengaja: saat JS set `display='flex'` chip row muncul flex, saat set `display='none'` tersembunyi.

- [ ] **Step 2: Tambah `_dopSelectionMeta` di blok state JS**

  Cari line ~1472:
  ```js
  const _dopSelected  = new Set();
  ```

  Ganti dengan:
  ```js
  const _dopSelected     = new Set();
  const _dopSelectionMeta = new Map();  // id → { nama, cat1 }
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add app/templates/payment_memo/index.html
  git commit -m "feat: add chips row HTML and _dopSelectionMeta state for SLA tab"
  ```

---

## Task 2: Tambah fungsi `dopRenderChips`, `dopRemoveChip`, `dopClearAllChips`

**Files:**
- Modify: `app/templates/payment_memo/index.html` — tambah 3 fungsi baru setelah `_dopUpdateInfo`

- [ ] **Step 1: Tambah tiga fungsi baru setelah `_dopUpdateInfo`**

  Cari baris `async function dopBulkUpdate()` (sekitar line 1692). Sisipkan blok berikut DI ATAS baris itu:

  ```js
  function dopRenderChips() {
    const row = document.getElementById('dop-chips-row');
    if (!row) return;
    if (_dopSelected.size === 0) { row.style.display = 'none'; return; }

    const ids    = [..._dopSelected];
    const LIMIT  = 5;
    const hidden = ids.length > LIMIT + 1 ? ids.slice(LIMIT) : [];
    const shown  = hidden.length ? ids.slice(0, LIMIT) : ids;

    function chipHtml(id) {
      const m = _dopSelectionMeta.get(id) || { nama: String(id), cat1: '' };
      const cat = m.cat1 ? `<span style="font-size:9px;opacity:.65;margin-left:3px">${m.cat1}</span>` : '';
      return `<span style="background:#1d4ed8;color:#fff;border-radius:99px;padding:2px 9px;font-size:11px;display:inline-flex;align-items:center;gap:3px;white-space:nowrap">` +
             `${m.nama}${cat}` +
             `<span onclick="dopRemoveChip(${id})" style="cursor:pointer;margin-left:3px;opacity:.8;font-size:10px" title="Hapus dari pilihan">✕</span></span>`;
    }

    let html = `<span style="font-size:10px;color:#1d4ed8;font-weight:700;white-space:nowrap;margin-right:2px">● Terpilih:</span>`;
    html += shown.map(chipHtml).join('');

    if (hidden.length) {
      html += `<span id="dop-chips-expand" onclick="dopExpandChips()" style="background:#dbeafe;color:#1d4ed8;border:1px solid #93c5fd;border-radius:99px;padding:2px 9px;font-size:11px;cursor:pointer;white-space:nowrap">+${hidden.length} lagi ▾</span>`;
      html += `<span id="dop-chips-hidden" style="display:none;display:contents">` + hidden.map(chipHtml).join('') + `</span>`;
    }

    html += `<span onclick="dopClearAllChips()" style="font-size:10px;color:#dc2626;cursor:pointer;margin-left:6px;white-space:nowrap">Hapus semua</span>`;

    row.innerHTML = html;
    row.style.display = 'flex';
  }

  function dopExpandChips() {
    const hidden = document.getElementById('dop-chips-hidden');
    const btn    = document.getElementById('dop-chips-expand');
    if (!hidden || !btn) return;
    const expanded = hidden.style.display !== 'none';
    hidden.style.display = expanded ? 'none' : 'contents';
    const n = _dopSelected.size - 5;
    btn.textContent = expanded ? `+${n} lagi ▾` : `▲ sembunyikan`;
  }

  function dopRemoveChip(id) {
    _dopSelected.delete(id);
    _dopSelectionMeta.delete(id);
    const cb = document.querySelector(`#dop-tbody .dop-cb[data-id="${id}"]`);
    if (cb) {
      cb.checked = false;
      const tr = cb.closest('tr');
      if (tr) {
        tr.style.background = '';
        if (tr.cells[2]) tr.cells[2].style.cssText = 'padding:6px 8px';
      }
    }
    _dopUpdateInfo();
    dopRenderChips();
  }

  function dopClearAllChips() {
    _dopSelected.clear();
    _dopSelectionMeta.clear();
    document.querySelectorAll('#dop-tbody .dop-cb').forEach(cb => {
      cb.checked = false;
      const tr = cb.closest('tr');
      if (tr) {
        tr.style.background = '';
        if (tr.cells[2]) tr.cells[2].style.cssText = 'padding:6px 8px';
      }
    });
    const sa = document.getElementById('dop-select-all');
    if (sa) sa.checked = false;
    _dopUpdateInfo();
    dopRenderChips();
  }
  ```

- [ ] **Step 2: Verifikasi manual di browser**

  Buka app → tab SLA → search nama apapun.  
  Buka DevTools console, jalankan:
  ```js
  _dopSelected.add(999);
  _dopSelectionMeta.set(999, { nama: 'Test Siswa', cat1: 'Kuliah' });
  dopRenderChips();
  ```
  Expected: chips row muncul biru dengan chip "Test Siswa · Kuliah ✕" dan "Hapus semua".  
  Klik ✕ → chip hilang.  
  Jalankan `dopClearAllChips()` → chips row hilang.

- [ ] **Step 3: Commit**

  ```bash
  git add app/templates/payment_memo/index.html
  git commit -m "feat: add dopRenderChips, dopRemoveChip, dopClearAllChips for SLA tab"
  ```

---

## Task 3: Fix `dopRenderRows` — jangan clear selection, re-apply highlight

**Files:**
- Modify: `app/templates/payment_memo/index.html:1497-1555`

- [ ] **Step 1: Update `dopRenderRows` — hapus `_dopSelected.clear()`, tambah re-apply logic**

  Cari blok sekitar line 1506–1554. Seluruh bagian `tb.innerHTML = rows.map(r => ...)` dan setelahnya. Ganti dengan versi yang:
  1. Tidak ada `_dopSelected.clear()`
  2. Tiap row dicek apakah ID-nya ada di `_dopSelected` → jika ya, tambah `checked` + style highlight

  Temukan:
  ```js
  tb.innerHTML = rows.map(r => `
      <tr class="dop-row"
          data-id="${r.id}"
  ```

  Ganti seluruh `tb.innerHTML = rows.map(r => ...)...join('')` sampai sebelum `_dopSelected.clear()` dengan:

  ```js
  tb.innerHTML = rows.map(r => {
    const sel = _dopSelected.has(r.id);
    const rowBg  = sel ? 'background:#eff6ff;' : '';
    const nameSt = sel ? 'color:#1d4ed8;font-weight:600;' : '';
    return `
      <tr class="dop-row"
          data-id="${r.id}"
          data-code="${(r.siswa_code||'').toLowerCase()}"
          data-nama="${(r.nama||'').toLowerCase()}"
          data-pam="${(r.pam_no||'').toLowerCase()}"
          data-cat1="${(r.cat1||'').toLowerCase()}"
          data-cat2="${(r.cat2||'').toLowerCase()}"
          data-perusahaan="${(r.perusahaan||'').toLowerCase()}"
          data-pillar="${(r.pillar||'').toLowerCase()}"
          style="border-bottom:1px solid #f1f5f9;${rowBg}">
        <td style="padding:6px;text-align:center">
          <input type="checkbox" class="dop-cb" data-id="${r.id}" ${sel ? 'checked' : ''} onchange="dopToggleCb(this)">
        </td>
        <td style="padding:6px 8px">${r.siswa_code||''}</td>
        <td style="padding:6px 8px;${nameSt}">${r.nama||'-'}</td>
        <td style="padding:6px 8px;font-family:monospace;color:#1d4ed8">${r.pam_no||''}</td>
        <td style="padding:6px 8px">${r.cat1||''}</td>
        <td style="padding:6px 8px">${r.cat2||''}</td>
        <td style="padding:6px 8px">${r.perusahaan||''}</td>
        <td style="padding:6px 8px">${r.pillar||''}</td>
        <td style="padding:6px 8px;text-align:right">Rp ${new Intl.NumberFormat('id-ID').format(r.amount||0)}</td>
        <td style="padding:6px 8px">${r.tanggal||''}</td>
        <td style="padding:6px 8px">${r.tgl_pengajuan||''}</td>
        <td style="padding:6px 8px">${r.tgl_receive||''}</td>
        <td style="padding:6px 8px">${r.tgl_pa||''}</td>
        <td style="padding:6px 8px">${r.tgl_final||''}</td>
        <td style="padding:6px 8px">${r.tgl_retur||''}</td>
        <td style="padding:6px 8px">${r.tgl_final6||''}</td>
        <td style="padding:6px 8px">${r.tgl_proses||''}</td>
        <td style="padding:6px 8px">${r.tgl_HT_AGRI||''}</td>
        <td style="padding:6px 8px">${r.tgl_Yurike_AGRI||''}</td>
        <td style="padding:6px 8px">${r.tgl_Aditya_AGRI||''}</td>
        <td style="padding:6px 8px">${r.tgl_Pedy_AGRI||''}</td>
        <td style="padding:6px 8px">${r.tgl_C2_AGRI||''}</td>
        <td style="padding:6px 8px">${r.tgl_MSIG_AGRI||''}</td>
        <td style="padding:6px 8px">${r.tgl_Paid_AGRI||''}</td>
        <td style="padding:6px 8px">${r['tgl_A-GS_APP']||''}</td>
        <td style="padding:6px 8px">${r['tgl_A-HJK_APP']||''}</td>
        <td style="padding:6px 8px">${r.tgl_ASPIRO_APP||''}</td>
        <td style="padding:6px 8px">${r.tgl_Paid_APP||''}</td>
      </tr>`;
  }).join('');
  ```

  Kemudian hapus baris:
  ```js
  _dopSelected.clear();
  const sa = document.getElementById('dop-select-all');
  if (sa) sa.checked = false;
  ```

  Ganti dengan (hanya reset select-all master checkbox):
  ```js
  const sa = document.getElementById('dop-select-all');
  if (sa) sa.checked = false;
  ```

- [ ] **Step 2: Verifikasi manual di browser**

  1. Buka app → tab SLA → search "a" (nama apapun yang ada hasilnya)
  2. Centang 2 baris
  3. Ubah search ke query berbeda (ketik nama lain → klik 🔍 Cari)
  4. Expected: chips row tetap tampil dengan 2 chip dari search sebelumnya
  5. Jika baris yang di-tick muncul di search baru → row harus langsung biru + tercentang

- [ ] **Step 3: Commit**

  ```bash
  git add app/templates/payment_memo/index.html
  git commit -m "feat: preserve selection across searches in SLA tab dopRenderRows"
  ```

---

## Task 4: Update `dopToggleCb` dan `dopToggleSelectAll` — sync meta + render chips

**Files:**
- Modify: `app/templates/payment_memo/index.html:1658-1676`

- [ ] **Step 1: Update `dopToggleCb`**

  Cari:
  ```js
  function dopToggleCb(cb) {
    const id = parseInt(cb.dataset.id, 10);
    if (cb.checked) _dopSelected.add(id);
    else            _dopSelected.delete(id);
    _dopUpdateInfo();
  }
  ```

  Ganti dengan:
  ```js
  function dopToggleCb(cb) {
    const id = parseInt(cb.dataset.id, 10);
    const tr = cb.closest('tr');
    if (cb.checked) {
      _dopSelected.add(id);
      if (tr) {
        const nama = tr.cells[2] ? tr.cells[2].textContent.trim() : '';
        const cat1 = tr.cells[4] ? tr.cells[4].textContent.trim() : '';
        _dopSelectionMeta.set(id, { nama, cat1 });
        tr.style.background = '#eff6ff';
        if (tr.cells[2]) tr.cells[2].style.cssText = 'color:#1d4ed8;font-weight:600;padding:6px 8px';
      }
    } else {
      _dopSelected.delete(id);
      _dopSelectionMeta.delete(id);
      if (tr) {
        tr.style.background = '';
        if (tr.cells[2]) tr.cells[2].style.cssText = 'padding:6px 8px';
      }
    }
    _dopUpdateInfo();
    dopRenderChips();
  }
  ```

- [ ] **Step 2: Update `dopToggleSelectAll`**

  Cari:
  ```js
  function dopToggleSelectAll(masterCb) {
    document.querySelectorAll('#dop-tbody .dop-row').forEach(row => {
      if (row.style.display === 'none') return;
      const cb = row.querySelector('.dop-cb');
      if (!cb) return;
      cb.checked = masterCb.checked;
      const id = parseInt(cb.dataset.id, 10);
      if (masterCb.checked) _dopSelected.add(id);
      else                  _dopSelected.delete(id);
    });
    _dopUpdateInfo();
  }
  ```

  Ganti dengan:
  ```js
  function dopToggleSelectAll(masterCb) {
    document.querySelectorAll('#dop-tbody .dop-row').forEach(row => {
      if (row.style.display === 'none') return;
      const cb = row.querySelector('.dop-cb');
      if (!cb) return;
      cb.checked = masterCb.checked;
      const id = parseInt(cb.dataset.id, 10);
      if (masterCb.checked) {
        _dopSelected.add(id);
        const nama = row.cells[2] ? row.cells[2].textContent.trim() : '';
        const cat1 = row.cells[4] ? row.cells[4].textContent.trim() : '';
        _dopSelectionMeta.set(id, { nama, cat1 });
        row.style.background = '#eff6ff';
        if (row.cells[2]) row.cells[2].style.cssText = 'color:#1d4ed8;font-weight:600;padding:6px 8px';
      } else {
        _dopSelected.delete(id);
        _dopSelectionMeta.delete(id);
        row.style.background = '';
        if (row.cells[2]) row.cells[2].style.cssText = 'padding:6px 8px';
      }
    });
    _dopUpdateInfo();
    dopRenderChips();
  }
  ```

- [ ] **Step 3: Verifikasi manual di browser**

  1. Search nama apapun → centang satu baris → chips row harus langsung muncul dengan 1 chip "Nama · Cat1"
  2. Centang satu lagi → chip kedua muncul
  3. Klik select-all checkbox → semua baris ter-check + semua chip muncul
  4. Uncheck select-all → chips hilang semua

- [ ] **Step 4: Commit**

  ```bash
  git add app/templates/payment_memo/index.html
  git commit -m "feat: sync _dopSelectionMeta and render chips on checkbox toggle in SLA tab"
  ```

---

## Task 5: Update `dopBulkUpdate` — clear meta + reset chips setelah berhasil

**Files:**
- Modify: `app/templates/payment_memo/index.html:1726-1729`

- [ ] **Step 1: Update blok `if (data.ok)` di `dopBulkUpdate`**

  Cari:
  ```js
  if (data.ok && _dopLastSearchQs) {
    // refresh current search results instead of full page reload
    setTimeout(() => _dopFetch(_dopLastSearchQs), 600);
  }
  ```

  Ganti dengan:
  ```js
  if (data.ok) {
    _dopSelected.clear();
    _dopSelectionMeta.clear();
    dopRenderChips();
    if (_dopLastSearchQs) setTimeout(() => _dopFetch(_dopLastSearchQs), 600);
  }
  ```

- [ ] **Step 2: Verifikasi manual di browser**

  1. Search, tick 2 baris, isi satu field tanggal, klik "Update Terpilih (2)"
  2. Setelah toast success: chips row harus hilang, counter kembali ke 0
  3. Hasil search refresh → baris tidak lagi tercentang

- [ ] **Step 3: Commit**

  ```bash
  git add app/templates/payment_memo/index.html
  git commit -m "feat: clear chip selection after successful bulk update in SLA tab"
  ```

---

## Task 6: End-to-end test multi-search scenario

Ini adalah acceptance test — tidak ada code baru, hanya verifikasi semua behaviour sesuai spec.

- [ ] **Buka app → tab SLA**

- [ ] **Skenario A — multi-search batch:**
  1. Search nama "a" → centang 2 baris → chips muncul
  2. Ganti search → ketik nama berbeda → 🔍 Cari
  3. Expected: chips dari skenario sebelumnya masih terlihat
  4. Centang 1 baris baru → chip ketiga muncul, counter = 3
  5. Isi satu tanggal → klik "Update Terpilih (3)" → success toast → chips hilang

- [ ] **Skenario B — de-select via chip:**
  1. Tick 3 baris
  2. Klik ✕ pada chip kedua
  3. Expected: chip hilang, counter turun ke 2, baris di tabel (jika tampil) otomatis uncheck

- [ ] **Skenario C — overflow:**
  1. Search broad → centang 7+ baris satu per satu
  2. Expected: setelah 6, chip row tampil "5 chip + +N lagi ▾"
  3. Klik "+N lagi ▾" → semua chip expand → badge berganti "▲ sembunyikan"

- [ ] **Skenario D — hapus semua:**
  1. Tick beberapa baris
  2. Klik "Hapus semua" di chips row
  3. Expected: chips row hilang, semua checkbox di tabel uncheck, counter = 0

- [ ] **Commit jika ada minor fix dari testing**

  ```bash
  git add app/templates/payment_memo/index.html
  git commit -m "fix: polish SLA chip selection from e2e testing"
  ```
