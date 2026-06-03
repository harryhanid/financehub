# ETF PA → Input Payment Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sambungkan ETF Payment Application ke Input Payment Beasiswa — saat add row, user pilih siswa + kategori dari PA draft, data auto-fill, dan status PA berubah sesuai lifecycle.

**Architecture:** Tambah 2 endpoint baru di etf_payment_application routes untuk search siswa draft dan get lines. Modifikasi `add_payment_multi` di beasiswa service untuk terima `etf_pa_line_id` dan trigger status PA. Update UI `ipayAddRow` agar siswa search ke endpoint baru dan cat1 dinamis dari PA lines.

**Tech Stack:** Python/Flask, SQLite, Vanilla JS (existing patterns di template beasiswa/index.html)

---

## File Map

| File | Perubahan |
|---|---|
| `app/database.py` | Tambah 5 kolom di DDL `payment_beasiswa` (etf_pa_line_id, tgl_pengajuan, tgl_receive, tgl_pa, tgl_final) + migration SQL |
| `app/modules/etf_payment_application/service.py` | Tambah `get_draft_siswa()` dan `get_draft_lines_for_siswa()`; update `update_pa()` auto-complete ke `complete` |
| `app/modules/etf_payment_application/routes.py` | Tambah route `/draft-siswa` dan `/draft-lines` |
| `app/modules/beasiswa/service.py` | Update `add_payment_multi()` untuk insert `etf_pa_line_id` dan update etf_pa status |
| `app/templates/beasiswa/index.html` | Update `ipayAddRow()` dan `ipaySave()` untuk ETF PA flow |

---

## Task 1: DB Migration — Tambah kolom yang kurang di payment_beasiswa

**Files:**
- Modify: `app/database.py`

- [ ] **Step 1: Tambah kolom ke DDL**

Di `app/database.py`, cari blok `CREATE TABLE IF NOT EXISTS payment_beasiswa`. Tambahkan kolom yang belum ada di DDL (tapi sudah dipakai di service):

```python
CREATE TABLE IF NOT EXISTS payment_beasiswa (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    siswa_code      TEXT NOT NULL,
    cat1            TEXT,
    cat2            TEXT,
    tanggal         TEXT,
    amount          REAL DEFAULT 0,
    pillar          TEXT,
    pam             TEXT,
    perusahaan      TEXT,
    cat3            TEXT,
    cat4            TEXT,
    memo_id         INTEGER REFERENCES payment_memo(id),
    tgl_pengajuan   TEXT,
    tgl_receive     TEXT,
    tgl_pa          TEXT,
    tgl_final       TEXT,
    etf_pa_line_id  INTEGER REFERENCES etf_pa_lines(id),
    status          TEXT DEFAULT 'draft',
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);
```

- [ ] **Step 2: Tambah migration SQL**

Di `app/database.py`, cari fungsi `init_db()` atau tempat migration dijalankan. Tambahkan migration idempoten untuk database yang sudah ada:

```python
MIGRATIONS = [
    "ALTER TABLE payment_beasiswa ADD COLUMN tgl_pengajuan TEXT",
    "ALTER TABLE payment_beasiswa ADD COLUMN tgl_receive TEXT",
    "ALTER TABLE payment_beasiswa ADD COLUMN tgl_pa TEXT",
    "ALTER TABLE payment_beasiswa ADD COLUMN tgl_final TEXT",
    "ALTER TABLE payment_beasiswa ADD COLUMN etf_pa_line_id INTEGER REFERENCES etf_pa_lines(id)",
]

def run_migrations(conn):
    for sql in MIGRATIONS:
        try:
            conn.execute(sql)
        except Exception:
            pass  # kolom sudah ada — SQLite error saat ADD COLUMN duplikat
    conn.commit()
```

Pastikan `run_migrations(conn)` dipanggil di `init_db()` setelah `conn.executescript(DDL)`.

- [ ] **Step 3: Verifikasi migration berjalan**

Jalankan app sekali dan cek schema:

```bash
python -c "
import sqlite3
conn = sqlite3.connect('app/data/financehub.db')
cols = [r[1] for r in conn.execute(\"PRAGMA table_info(payment_beasiswa)\").fetchall()]
print(cols)
assert 'etf_pa_line_id' in cols
assert 'tgl_pengajuan' in cols
print('OK')
"
```

Expected output: list kolom termasuk `etf_pa_line_id`, `tgl_pengajuan`, `tgl_receive`, `tgl_pa`, `tgl_final`, lalu `OK`.

- [ ] **Step 4: Commit**

```bash
git add app/database.py
git commit -m "feat(db): add etf_pa_line_id and tgl_* columns to payment_beasiswa"
```

---

## Task 2: Service ETF PA — Tambah fungsi draft-siswa dan draft-lines

**Files:**
- Modify: `app/modules/etf_payment_application/service.py`

- [ ] **Step 1: Tambah `get_draft_siswa()`**

Tambahkan fungsi ini di akhir `service.py`, sebelum fungsi export:

```python
def get_draft_siswa(company_id: int, q: str) -> list:
    """Return siswa yang punya minimal 1 PA line di mana PA status='draft'."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT DISTINCT s.id, s.code, s.nama, s.jenjang, s.universitas
           FROM siswa s
           JOIN etf_pa_lines l ON l.student_id = s.id
           JOIN etf_pa p ON p.id = l.pa_id
           WHERE p.company_id = ? AND p.status = 'draft'
             AND (s.nama LIKE ? OR s.code LIKE ?)
           ORDER BY s.nama
           LIMIT 20""",
        (company_id, f"%{q}%", f"%{q}%")
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 2: Tambah `get_draft_lines_for_siswa()`**

Tambahkan fungsi berikutnya:

```python
def get_draft_lines_for_siswa(company_id: int, siswa_id: int) -> list:
    """Return semua PA lines milik siswa dengan PA status='draft'."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT l.id AS line_id, l.pa_id, p.pa_number,
                  l.jenis_pembayaran, l.jumlah_pembayaran,
                  p.tgl_surat_pengajuan,
                  p.doc_received_by_educ,
                  p.tgl_payment_application
           FROM etf_pa_lines l
           JOIN etf_pa p ON p.id = l.pa_id
           WHERE p.company_id = ? AND p.status = 'draft'
             AND l.student_id = ?
           ORDER BY p.created_at DESC""",
        (company_id, siswa_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 3: Update `update_pa()` — auto-complete saat tanggal_bayar diisi**

Di fungsi `update_pa()`, cari baris yang menentukan `new_status`. Ganti logika berikut:

Cari:
```python
new_status  = data.get("status", row["status"])
```

Ganti dengan:
```python
new_status = data.get("status", row["status"])
if data.get("tanggal_bayar"):
    new_status = "complete"
```

Ini memastikan tanggal_bayar terisi → status otomatis complete, apapun yang dikirim di field status.

- [ ] **Step 4: Commit**

```bash
git add app/modules/etf_payment_application/service.py
git commit -m "feat(etf-pa): add get_draft_siswa, get_draft_lines_for_siswa; auto-complete on tanggal_bayar"
```

---

## Task 3: Routes ETF PA — Expose endpoint draft-siswa dan draft-lines

**Files:**
- Modify: `app/modules/etf_payment_application/routes.py`

- [ ] **Step 1: Import fungsi baru**

Di bagian import routes, tambahkan dua fungsi ke import dari service:

```python
from modules.etf_payment_application.service import (
    get_pa_list, get_pa_flat, get_pa_header, bulk_update_pa, export_pa_excel,
    create_pa, update_pa, get_pa_lines, get_siswa_autocomplete,
    get_draft_siswa, get_draft_lines_for_siswa,
)
```

- [ ] **Step 2: Tambah route `/draft-siswa`**

Tambahkan route baru setelah route `siswa_search`:

```python
@bp.route("/draft-siswa")
@jwt_html_required
def draft_siswa():
    q          = request.args.get("q", "")
    company_id = session.get("company_id")
    return jsonify(get_draft_siswa(company_id, q))
```

- [ ] **Step 3: Tambah route `/draft-lines`**

Tambahkan route baru berikutnya:

```python
@bp.route("/draft-lines")
@jwt_html_required
def draft_lines():
    siswa_id   = request.args.get("siswa_id", type=int)
    company_id = session.get("company_id")
    if not siswa_id:
        return jsonify([])
    return jsonify(get_draft_lines_for_siswa(company_id, siswa_id))
```

- [ ] **Step 4: Verifikasi endpoint bisa diakses**

Jalankan Flask dev server dan test manual di browser (login dulu):

```
GET /etf-payment-application/draft-siswa?q=
```

Expected: JSON array (bisa kosong `[]` jika belum ada PA draft).

- [ ] **Step 5: Commit**

```bash
git add app/modules/etf_payment_application/routes.py
git commit -m "feat(etf-pa): expose /draft-siswa and /draft-lines endpoints"
```

---

## Task 4: Beasiswa Service — add_payment_multi terima etf_pa_line_id

**Files:**
- Modify: `app/modules/beasiswa/service.py`

- [ ] **Step 1: Update INSERT di add_payment_multi untuk include etf_pa_line_id**

Di fungsi `add_payment_multi`, cari bagian INSERT ke `payment_beasiswa`. Ganti:

```python
cur = conn.execute(
    """INSERT INTO payment_beasiswa
       (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,
        tgl_pengajuan,tgl_receive,tgl_pa,tgl_final,cat3,cat4,status)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'draft')""",
    (company_id, siswa_code,
     row.get("cat1", ""), row.get("cat2", ""),
     tanggal, amount, pillar, perusahaan,
     row.get("tgl_pengajuan", ""), row.get("tgl_receive", ""),
     row.get("tgl_pa", ""),   row.get("tgl_final", ""),
     row.get("cat3", ""),     row.get("cat4", ""))
)
```

Dengan:

```python
etf_pa_line_id = row.get("etf_pa_line_id") or None
cur = conn.execute(
    """INSERT INTO payment_beasiswa
       (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,
        tgl_pengajuan,tgl_receive,tgl_pa,tgl_final,cat3,cat4,etf_pa_line_id,status)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'draft')""",
    (company_id, siswa_code,
     row.get("cat1", ""), row.get("cat2", ""),
     tanggal, amount, pillar, perusahaan,
     row.get("tgl_pengajuan", ""), row.get("tgl_receive", ""),
     row.get("tgl_pa", ""),   row.get("tgl_final", ""),
     row.get("cat3", ""),     row.get("cat4", ""),
     etf_pa_line_id)
)
```

- [ ] **Step 2: Collect etf_pa_line_ids dan update PA status**

Setelah loop insert rows dan sebelum `create_pam_record`, tambahkan blok update status ETF PA:

```python
# Update etf_pa status → on_process untuk PA yang di-referensi
pa_line_ids = [
    row.get("etf_pa_line_id")
    for row in rows
    if row.get("etf_pa_line_id") and float(str(row.get("amount", 0)).replace(",", "") or 0) > 0
]
if pa_line_ids:
    ph = ",".join("?" * len(pa_line_ids))
    conn.execute(
        f"""UPDATE etf_pa SET status = 'on_process', updated_at = ?
            WHERE id IN (
                SELECT DISTINCT pa_id FROM etf_pa_lines WHERE id IN ({ph})
            ) AND company_id = ? AND status = 'draft'""",
        [_ts()] + pa_line_ids + [company_id]
    )
```

Letakkan blok ini tepat sebelum baris `pam_no = create_pam_record(...)`.

- [ ] **Step 3: Commit**

```bash
git add app/modules/beasiswa/service.py
git commit -m "feat(beasiswa): add_payment_multi accepts etf_pa_line_id and triggers PA on_process"
```

---

## Task 5: UI — Update ipayAddRow untuk ETF PA flow

**Files:**
- Modify: `app/templates/beasiswa/index.html`

- [ ] **Step 1: Tambah hidden field etf_pa_line_id per row**

Di fungsi `ipayAddRow()`, setelah deklarasi `tr.dataset.siswaCode = ""`, tambahkan:

```javascript
tr.dataset.etfPaLineId = "";
tr.dataset.etfSiswaId  = "";
```

Di deklarasi row struct, tambahkan hidden input untuk line_id (akan di-set saat user pilih kategori):

```javascript
// Hidden ETF PA line id
const hidEtfLineId = document.createElement("input");
hidEtfLineId.type = "hidden";
hidEtfLineId.value = "";
tr._hidEtfLineId = hidEtfLineId;
tdSiswa.appendChild(hidEtfLineId);
```

- [ ] **Step 2: Ganti siswa search untuk query endpoint /draft-siswa**

Di dalam `ipayAddRow()`, ganti event listener `siswaInp.addEventListener("input", ...)` yang saat ini search dari `SISWA_LIST` (frontend cache).

Ganti seluruh blok listener tersebut dengan:

```javascript
siswaInp.addEventListener("input", () => {
  const q = siswaInp.value.trim();
  sugg.innerHTML = "";
  if (!q) { sugg.style.display = "none"; return; }
  apiFetch(`/etf-payment-application/draft-siswa?q=${encodeURIComponent(q)}`)
    .then(r => r.json())
    .then(hits => {
      if (!hits.length) {
        sugg.innerHTML = `<div style="padding:10px 12px;font-size:.875rem;color:#6b7280">Tidak ada siswa dengan PA draft.</div>`;
        _positionSugg(); sugg.style.display = "block"; return;
      }
      sugg.innerHTML = "";
      hits.forEach(s => {
        const d = document.createElement("div");
        d.style.cssText = "padding:8px 12px;cursor:pointer;font-size:.875rem;border-bottom:1px solid #f3f4f6;display:flex;align-items:center;gap:.5rem";
        d.innerHTML = `<span style="font-weight:600;color:#1a56db;min-width:72px">${s.code}</span><span style="color:#374151">${s.nama}</span>`;
        d.addEventListener("mousedown", () => {
          siswaInp.value = `${s.code} — ${s.nama}`;
          tr.dataset.siswaCode  = s.code;
          tr.dataset.etfSiswaId = s.id;
          sugg.style.display = "none";
          tr._hidEtfLineId.value = "";
          // Reset cat1 dropdown dan load lines
          sCat1.innerHTML = `<option value="">Memuat...</option>`;
          sCat1.disabled = true;
          apiFetch(`/etf-payment-application/draft-lines?siswa_id=${s.id}`)
            .then(r => r.json())
            .then(lines => {
              sCat1.innerHTML = `<option value="">— Pilih Kategori 1 —</option>` +
                lines.map(l => `<option value="${l.jenis_pembayaran}" data-line='${JSON.stringify(l)}'>${l.jenis_pembayaran} (${l.pa_number})</option>`).join("");
              sCat1.disabled = false;
            });
          // Load sisa budget
          tr._sisaBudget = {};
          tr._sisaCell.textContent = "Memuat...";
          tr._sisaCell.style.color = "#6b7280";
          apiFetch(`/beasiswa/siswa/${s.code}/sisa-budget`).then(r => r.json()).then(data => {
            tr._sisaBudget = data.sisa || {};
            _ipayUpdateSisaCell(tr);
          });
        });
        d.addEventListener("mouseover",  () => { d.style.background = "#eff6ff"; });
        d.addEventListener("mouseout",   () => { d.style.background = ""; });
        sugg.appendChild(d);
      });
      _positionSugg();
      sugg.style.display = "block";
    });
});
```

- [ ] **Step 3: Update event listener sCat1 onChange untuk auto-fill fields**

Ganti event listener `sCat1.addEventListener("change", ...)` yang sebelumnya hanya memanggil `_ipayUpdateSisaCell(tr)`:

```javascript
sCat1.addEventListener("change", () => {
  _ipayUpdateSisaCell(tr);
  const opt = sCat1.options[sCat1.selectedIndex];
  if (!opt || !opt.dataset.line) {
    tr._hidEtfLineId.value = "";
    tr._amtInp.value = "";
    tr._amtInp.readOnly = false;
    tr._tgls[0].value = "";
    tr._tgls[1].value = "";
    tr._tgls[2].value = "";
    tr._tgls[0].readOnly = false;
    tr._tgls[1].readOnly = false;
    tr._tgls[2].readOnly = false;
    return;
  }
  const line = JSON.parse(opt.dataset.line);
  tr._hidEtfLineId.value  = line.line_id;
  tr._amtInp.value        = line.jumlah_pembayaran || "";
  tr._amtInp.readOnly     = true;
  tr._tgls[0].value       = line.tgl_surat_pengajuan      || "";
  tr._tgls[1].value       = line.doc_received_by_educ     || "";
  tr._tgls[2].value       = line.tgl_payment_application  || "";
  tr._tgls[0].readOnly    = true;
  tr._tgls[1].readOnly    = true;
  tr._tgls[2].readOnly    = true;
  ipayUpdateTotal();
  _ipayUpdateSisaCell(tr);
});
```

- [ ] **Step 4: Buat sCat1 awalnya disabled (sebelum siswa dipilih)**

Tepat setelah `sCat1` dibuat (baris `sCat1.style.width = "100%"`), tambahkan:

```javascript
sCat1.disabled = true;
sCat1.title = "Pilih siswa dulu";
```

- [ ] **Step 5: Update ipaySave() untuk include etf_pa_line_id dalam rows**

Di fungsi `ipaySave()`, cari blok:

```javascript
const rows = allTrs.map(tr => ({
  siswa_code:    tr.dataset.siswaCode || "",
  cat1:          tr._cat1Select.value,
  cat2:          tr._cat2Drop._hid.value,
  amount:        parseFloat(tr._amtInp.value) || 0,
  tgl_pengajuan: tr._tgls[0].value,
  tgl_receive:   tr._tgls[1].value,
  tgl_pa:        tr._tgls[2].value,
  tgl_final:     tr._tgls[3].value,
})).filter(r => r.amount > 0);
```

Ganti dengan:

```javascript
const rows = allTrs.map(tr => ({
  siswa_code:       tr.dataset.siswaCode || "",
  cat1:             tr._cat1Select.value,
  cat2:             tr._cat2Drop._hid.value,
  amount:           parseFloat(tr._amtInp.value) || 0,
  tgl_pengajuan:    tr._tgls[0].value,
  tgl_receive:      tr._tgls[1].value,
  tgl_pa:           tr._tgls[2].value,
  tgl_final:        tr._tgls[3].value,
  etf_pa_line_id:   tr._hidEtfLineId?.value ? parseInt(tr._hidEtfLineId.value) : null,
})).filter(r => r.amount > 0);
```

- [ ] **Step 6: Commit**

```bash
git add app/templates/beasiswa/index.html
git commit -m "feat(ui): ETF PA integration in ipayAddRow — draft siswa search, dynamic cat1, auto-fill dates"
```

---

## Task 6: Verifikasi End-to-End

- [ ] **Step 1: Pastikan ada PA dengan status draft**

Buka menu ETF Payment Application, buat PA baru dengan minimal 1 siswa dan 1 jenis pembayaran. Pastikan status = `draft`.

- [ ] **Step 2: Test add row di Input Payment**

Buka tab Input Payment di Beasiswa:
- Klik "+ Tambah Baris"
- Ketik nama siswa yang punya PA draft → pastikan suggestion muncul hanya siswa ETF
- Pilih siswa → dropdown Kategori 1 muncul dengan label `jenis_pembayaran (PA/ETF/xxx/yyyy)`
- Pilih kategori → Amount, Tgl Pengajuan, Tgl Receive, Tgl PA auto-fill dan read-only
- Isi Kategori 2 dan Tgl Final manual
- Isi Tanggal, Perusahaan, PAM header
- Klik Simpan Payment

- [ ] **Step 3: Verifikasi status PA berubah ke on_process**

Buka menu ETF Payment Application → cari PA yang tadi dipakai → pastikan kolom status = `on_process`.

- [ ] **Step 4: Test tanggal_bayar → complete**

Di ETF Payment Application, edit PA tersebut → isi field Tgl Bayar → save. Verifikasi status berubah ke `complete`.

- [ ] **Step 5: Verifikasi PA complete tidak muncul di autocomplete**

Kembali ke Input Payment, tambah baris baru, ketik nama siswa yang PA-nya sudah `complete` → pastikan **tidak muncul** di suggestion.

- [ ] **Step 6: Final commit jika ada fix minor**

```bash
git add -p
git commit -m "fix: address e2e verification findings"
```
