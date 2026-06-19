# Design: Open PAM — Grouped Accordion per PAM No

**Date:** 2026-06-19  
**Module:** `payment_memo` — tab "Open PAM"  
**Scope:** Frontend only — no backend changes

---

## Problem

Tab "Open PAM" saat ini menampilkan flat list dari `payment_beasiswa` rows dengan `status = 'open'`. Kalau satu PAM punya 5 siswa, muncul 5 baris terpisah — sulit dibaca dan tidak memberikan gambaran per-PAM.

## Goal

Tampilkan tab "Open PAM" **per PAM No** (grouped). Satu baris = satu PAM. Klik baris → detail items muncul inline (accordion/expandable row).

---

## Design Decisions

| Keputusan | Pilihan |
|---|---|
| Cara buka detail | Expandable row (accordion inline — Option A) |
| Checkbox behavior | Checkbox di level PAM — centang satu PAM = select semua items-nya (Option C) |
| Items tanpa PAM No | Grup terpisah "Belum di-assign" di bagian paling bawah (Option B) |
| Implementasi grouping | Client-side JavaScript — tidak ada backend change (Approach A) |
| Konten kolom Keterangan | `nama` siswa dari tiap item, comma-separated, truncate 3+N |

---

## Layout

### Master Row (per PAM No)

| Kolom | Konten | Sumber |
|---|---|---|
| Checkbox | Select seluruh items PAM tersebut | — |
| Toggle `▶/▼` | Expand/collapse detail | — |
| PAM No | Nomor PAM (monospace, biru) | `payment_beasiswa.pam` |
| Pillar | Badge warna (AGRI/APP/LAND/SETF) | Derived dari prefix PAM No |
| Tanggal | Tanggal terkecil dari items dalam grup | `min(tanggal)` di JS |
| Keterangan | Nama siswa comma-separated, max 3 + "(+N lagi)" | `item.nama`, join dengan ", " |
| Jml | Count items dalam grup | `items.length` |
| Total Amount | Sum amount semua items | `sum(amount)` di JS |
| Status | Badge "Open" | hardcoded (tab ini filter open saja) |

### Detail Rows (expanded, per item)

Muncul inline di bawah master row saat di-expand. Kolom:
- Code (`siswa_code`)
- Nama (`nama`)
- Kategori (`cat1 / cat2`)
- Tanggal (`tanggal`)
- Amount
- Aksi: tombol **Edit** dan **Hapus** (sama persis dengan tampilan sekarang)

### Grup "Belum di-assign"

- Row header berwarna amber (`#fef3c7`) di bagian paling bawah setelah semua PAM
- Label: `⚠ Belum di-assign ke PAM`
- Bisa di-expand sama seperti PAM group lain
- Items: semua `payment_beasiswa` dengan `pam = null`, `''`, atau `'--'`

### Grand Total Bar

Row footer di paling bawah tabel menampilkan:
- Total item count
- Grand total amount

### Memo Bar

Muncul di bawah tabel saat ada PAM di-centang:
- Label: "N PAM dipilih — klik Buat Memo untuk lanjut"
- Tombol "📄 Buat Memo" → trigger fungsi memo creation yang sudah ada

---

## JavaScript Logic

### Grouping Function

```javascript
function groupDraftsByPAM(drafts) {
  const groups = {};
  const UNASSIGNED = '__unassigned__';

  drafts.forEach(d => {
    const key = (d.pam && d.pam !== '--') ? d.pam : UNASSIGNED;
    if (!groups[key]) {
      groups[key] = { pam: key, items: [], total: 0, minDate: d.tanggal };
    }
    groups[key].items.push(d);
    groups[key].total += d.amount;
    if (d.tanggal < groups[key].minDate) groups[key].minDate = d.tanggal;
  });

  // Sort: assigned PAMs alphabetically, unassigned last
  const keys = Object.keys(groups)
    .filter(k => k !== UNASSIGNED)
    .sort()
    .concat(groups[UNASSIGNED] ? [UNASSIGNED] : []);

  return keys.map(k => groups[k]);
}
```

### Keterangan (nama) Builder

```javascript
function buildKeterangan(items, max = 3) {
  const names = items.map(d => d.nama || d.siswa_code || '--');
  if (names.length <= max) return names.join(', ');
  return names.slice(0, max).join(', ') + ` (+${names.length - max} lagi)`;
}
```

### Pillar Badge

```javascript
function getPillarFromPamNo(pamNo) {
  if (!pamNo || pamNo === '--') return null;
  const prefix = pamNo.split('/')[0].toUpperCase();
  const map = { AGRI: 'agri', APP: 'app', LAND: 'land', SETF: 'setf', SML: 'land' };
  return map[prefix] || null;
}
```

### Checkbox Propagation

- PAM-level checkbox `onchange` → find all `.draft-check[data-pam-group="<pamKey>"]` → set `checked` sama
- Select-all header checkbox → toggle semua PAM checkboxes
- Existing memo creation logic membaca `.draft-check:checked` — tetap berfungsi karena item checkboxes masih ada di DOM (hidden dalam detail rows)

---

## Implementation Scope

**File yang diubah:** `app/templates/payment_memo/index.html` saja.

**Perubahan:**
1. Ganti isi `<tbody>` di `#tab-draft-pay` dari server-rendered Jinja loop menjadi JS-rendered
2. Tambah fungsi `renderOpenPAM(drafts)` — grouping + render accordion
3. Tambah fungsi `togglePAMRow(key)` — expand/collapse
4. Update checkbox propagation logic
5. Tambah memo bar (muncul saat ada selection)
6. Hapus Jinja loop `{% for d in drafts %}` yang lama (data tetap dipass ke JS via `const DRAFTS = {{ drafts | tojson }}`)

**Tidak berubah:**
- `service.py` — `get_draft_payments()` tetap return flat list
- `routes.py` — tidak ada endpoint baru
- `api.py` — tidak ada perubahan
- Fungsi Edit draft, Hapus draft, Export Excel — tetap berfungsi

---

## Edge Cases

| Kasus | Handling |
|---|---|
| PAM No null / `'--'` | Masuk grup "Belum di-assign" |
| Semua drafts sudah punya PAM No | Grup "Belum di-assign" tidak muncul |
| PAM hanya punya 1 item | Master row tetap tampil normal, expand menunjukkan 1 baris |
| Nama siswa null | Fallback ke `siswa_code`, lalu `'--'` |
| `drafts` kosong | Tampilkan pesan "Tidak ada payment draft." seperti sekarang |
