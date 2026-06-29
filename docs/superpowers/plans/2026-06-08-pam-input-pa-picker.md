# PAM Input — PA Picker Sub-Row Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Setelah memilih Nama + Cat1 + Cat2, jika ada 2+ PA yang cocok tampilkan sub-row dengan mini-table No PA + Amount supaya user bisa pilih yang tepat sebelum data di-fill otomatis.

**Architecture:** Perubahan hanya di satu file template (`payment_memo/index.html`). Tambah helper function `_ipayBuildPickerRow`, ubah cat2 change handler untuk menampilkan picker jika candidates > 1, tambah cleanup di cat1 change handler dan delete button.

**Tech Stack:** Vanilla JS inline di Jinja2 HTML template (Flask). Tidak ada backend changes.

---

## File yang Dimodifikasi

- `app/templates/payment_memo/index.html` — satu-satunya file yang berubah

---

### Task 1: Tambah helper `_ipayBuildPickerRow` setelah `_ipayFillLine`

**Files:**
- Modify: `app/templates/payment_memo/index.html` (setelah line 2422)

- [ ] **Step 1: Sisipkan fungsi `_ipayBuildPickerRow` setelah baris penutup `_ipayFillLine`**

Cari teks ini (baris 2422):
```javascript
  ipayUpdateTotal(); _ipayUpdateSisaCell(tr);
}

// ── Input Payment tab ─────────────────────────────────────────────────────────
```

Ganti dengan:
```javascript
  ipayUpdateTotal(); _ipayUpdateSisaCell(tr);
}

function _ipayBuildPickerRow(tr, candidates) {
  const pr = document.createElement("tr");
  pr.className = "ipay-pa-picker-row";
  const td = document.createElement("td");
  td.colSpan = 10;
  td.style.cssText = "padding:4px 8px 10px 24px;background:#eff6ff;border-top:1px solid #bfdbfe";
  const title = document.createElement("div");
  title.style.cssText = "font-size:10px;font-weight:700;color:#1d4ed8;text-transform:uppercase;letter-spacing:.04em;margin-bottom:5px";
  title.textContent = candidates.length + " PA ditemukan — pilih salah satu:";
  const tbl = document.createElement("table");
  tbl.style.cssText = "border-collapse:collapse;font-size:.8rem";
  tbl.innerHTML = `<thead><tr style="background:#dbeafe">
    <th style="padding:4px 10px;text-align:left;font-weight:700;color:#1e40af;border:1px solid #bfdbfe">No PA</th>
    <th style="padding:4px 10px;text-align:right;font-weight:700;color:#1e40af;border:1px solid #bfdbfe">Amount (Rp)</th>
  </tr></thead>`;
  const tbody = document.createElement("tbody");
  candidates.forEach((line, i) => {
    const row = document.createElement("tr");
    const bg0 = i % 2 === 0 ? "#fff" : "#f8fafc";
    row.style.cssText = "cursor:pointer;background:" + bg0;
    row.innerHTML = `
      <td style="padding:5px 10px;border:1px solid #e2e8f0;font-family:monospace;font-size:.78rem;color:#1d4ed8">${line.pa_number}</td>
      <td style="padding:5px 10px;border:1px solid #e2e8f0;text-align:right;font-weight:600">Rp ${new Intl.NumberFormat('id-ID').format(line.jumlah_pembayaran||0)}</td>`;
    row.addEventListener("mouseover", () => { row.style.background = "#eff6ff"; });
    row.addEventListener("mouseout",  () => { row.style.background = bg0; });
    row.addEventListener("click", () => { _ipayFillLine(tr, line); pr.remove(); tr._paPickerRow = null; });
    tbody.appendChild(row);
  });
  tbl.appendChild(tbody);
  td.appendChild(title); td.appendChild(tbl); pr.appendChild(td);
  return pr;
}

// ── Input Payment tab ─────────────────────────────────────────────────────────
```

- [ ] **Step 2: Verifikasi manual** — Buka browser, inspect console, pastikan tidak ada syntax error saat halaman dimuat.

- [ ] **Step 3: Commit**
```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add _ipayBuildPickerRow helper for PA picker sub-row"
```

---

### Task 2: Update cat2 change handler — tampilkan picker jika 2+ candidates

**Files:**
- Modify: `app/templates/payment_memo/index.html` (sekitar line 2670–2690)

- [ ] **Step 1: Ganti isi cat2 change handler**

Cari teks ini (persis, termasuk whitespace):
```javascript
  cat2Drop._hid.addEventListener("change", () => {
    const selectedCat1 = sCat1.value;
    const selectedCat2 = cat2Drop._hid.value;
    if (selectedCat1 && selectedCat2) {
      const line = (tr._allLines||[]).find(l => l.jenis_pembayaran === selectedCat1 && l.semester === selectedCat2)
               || (tr._allLines||[]).find(l => l.jenis_pembayaran === selectedCat1 && (l.tahun_ajaran === selectedCat2 || selectedCat2 === '—'));
      if (line) _ipayFillLine(tr, line);
    }
    const isMed = _isMedical(selectedCat1, selectedCat2);
```

Ganti dengan:
```javascript
  cat2Drop._hid.addEventListener("change", () => {
    const selectedCat1 = sCat1.value;
    const selectedCat2 = cat2Drop._hid.value;
    // Remove existing picker before rebuilding
    tr._paPickerRow?.remove(); tr._paPickerRow = null;
    if (selectedCat1 && selectedCat2) {
      const candidates = (tr._allLines||[]).filter(l =>
        l.jenis_pembayaran === selectedCat1 && (
          l.semester === selectedCat2 ||
          l.tahun_ajaran === selectedCat2 ||
          selectedCat2 === '—'
        )
      );
      if (candidates.length === 1) {
        _ipayFillLine(tr, candidates[0]);
      } else if (candidates.length > 1) {
        _ipayResetAutoFill(tr);
        const pr = _ipayBuildPickerRow(tr, candidates);
        tr._paPickerRow = pr;
        medisRow.parentNode.insertBefore(pr, medisRow.nextSibling);
      }
    }
    const isMed = _isMedical(selectedCat1, selectedCat2);
```

- [ ] **Step 2: Verifikasi manual**
  1. Buka halaman Payment Memo → tab Input
  2. Klik "+ Tambah Baris"
  3. Cari siswa yang punya 1 PA → pilih cat1 → pilih cat2: amount harus langsung terisi (1 candidate)
  4. Cari siswa yang punya 2+ PA dengan cat1+cat2 yang sama → pilih: harus muncul sub-row biru di bawah baris dengan daftar No PA + Amount
  5. Klik salah satu baris di sub-row: amount harus terisi, sub-row harus hilang

- [ ] **Step 3: Commit**
```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: show PA picker sub-row when 2+ PAs match cat1+cat2"
```

---

### Task 3: Cleanup — hapus picker saat cat1 berubah atau baris dihapus

**Files:**
- Modify: `app/templates/payment_memo/index.html` (cat1 handler ~line 2629, delete button ~line 2699)

- [ ] **Step 1: Tambah cleanup di cat1 change handler**

Cari teks ini:
```javascript
  sCat1.addEventListener("change", () => {
    const selectedCat1 = sCat1.value;
    // Reset Cat2 and auto-fill whenever Cat1 changes
    cat2Drop.setOpts([]);
    _ipayResetAutoFill(tr);
```

Ganti dengan:
```javascript
  sCat1.addEventListener("change", () => {
    const selectedCat1 = sCat1.value;
    // Reset Cat2, auto-fill, and picker whenever Cat1 changes
    tr._paPickerRow?.remove(); tr._paPickerRow = null;
    cat2Drop.setOpts([]);
    _ipayResetAutoFill(tr);
```

- [ ] **Step 2: Tambah cleanup di delete button**

Cari teks ini (line ~2699):
```javascript
  btnDel.addEventListener("click",()=>{sugg.remove();cat2Drop._pan?.remove();tr.remove();medisRow.remove();ipayUpdateTotal();
```

Ganti dengan:
```javascript
  btnDel.addEventListener("click",()=>{sugg.remove();cat2Drop._pan?.remove();tr._paPickerRow?.remove();tr.remove();medisRow.remove();ipayUpdateTotal();
```

- [ ] **Step 3: Verifikasi manual**
  1. Muncul sub-row picker (2+ PA match) → ubah Cat1 → sub-row harus hilang
  2. Muncul sub-row picker → klik ✕ (hapus baris) → sub-row harus hilang bersama baris

- [ ] **Step 4: Commit**
```bash
git add app/templates/payment_memo/index.html
git commit -m "fix: cleanup PA picker sub-row on cat1 change and row delete"
```
