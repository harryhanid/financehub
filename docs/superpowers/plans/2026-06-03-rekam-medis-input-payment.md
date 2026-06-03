# Rekam Medis — Input Payment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambah section Data Medis (tabel `rekam_medis`) yang wajib diisi saat row Input Payment memiliki cat1="By Medical" dan cat2="Rawat Jalan"/"Rawat Inap".

**Architecture:** Tabel baru `rekam_medis` dengan FK ke `payment_beasiswa.id`. Data dikirim embedded dalam payload `tambah-multi` yang sudah ada dan disimpan dalam satu transaksi. Frontend menambah sub-row expand/collapse per row By Medical di `ipayAddRow()`.

**Tech Stack:** Python/Flask (SQLite), Jinja2, Vanilla JS (DOM manipulation)

---

## File Map

| File | Perubahan |
|---|---|
| `app/database.py` | CREATE TABLE rekam_medis + migrasi existing DB |
| `app/modules/beasiswa/service.py` | `add_payment_multi()` — insert rekam_medis per row By Medical, validasi backend |
| `app/templates/payment_memo/index.html` | `ipayAddRow()` — sub-row Data Medis; `ipaySave()` — validasi + kirim data |
| `app/tests/test_beasiswa_service.py` | Test `add_payment_multi` dengan rekam_medis |

---

## Task 1: DB — Tabel `rekam_medis`

**Files:**
- Modify: `app/database.py`

- [ ] **Step 1: Tambah CREATE TABLE di schema string**

Buka `app/database.py`. Cari baris `CREATE TABLE IF NOT EXISTS klaim_medical` (sekitar baris 139). Tambah tabel baru **setelah** klaim_medical:

```python
# Setelah blok CREATE TABLE klaim_medical (...)
CREATE TABLE IF NOT EXISTS rekam_medis (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER NOT NULL,
    payment_id   INTEGER NOT NULL REFERENCES payment_beasiswa(id),
    siswa_code   TEXT NOT NULL,
    kelas        TEXT NOT NULL,
    rumah_sakit  TEXT NOT NULL,
    diagnosa     TEXT NOT NULL,
    spesialisasi TEXT NOT NULL,
    catatan      TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);
```

Tambahkan string SQL di dalam `CREATE_SQL` (atau dalam string multiline yang digunakan `init_db()`). Ikuti pola tabel lain yang ada.

- [ ] **Step 2: Tambah migrasi di fungsi `migrate_db()`**

Di dalam fungsi `migrate_db()` (cari pola `try: conn.execute("ALTER TABLE..."`), tambah blok migrasi untuk existing DB:

```python
# rekam_medis table (new — safe to run on existing DBs)
try:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rekam_medis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            payment_id INTEGER NOT NULL,
            siswa_code TEXT NOT NULL,
            kelas TEXT NOT NULL,
            rumah_sakit TEXT NOT NULL,
            diagnosa TEXT NOT NULL,
            spesialisasi TEXT NOT NULL,
            catatan TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
    )
    conn.commit()
except Exception:
    pass
```

- [ ] **Step 3: Verifikasi tabel terbuat**

```bash
python -c "
import sys; sys.path.insert(0,'app')
import config; config.DB_PATH = 'app/finance_hub.db'
from database import migrate_db, get_conn
migrate_db()
c = get_conn()
cols = c.execute('PRAGMA table_info(rekam_medis)').fetchall()
print([r[1] for r in cols])
"
```

Expected output: `['id', 'company_id', 'payment_id', 'siswa_code', 'kelas', 'rumah_sakit', 'diagnosa', 'spesialisasi', 'catatan', 'created_at']`

- [ ] **Step 4: Commit**

```bash
git add app/database.py
git commit -m "feat(db): add rekam_medis table"
```

---

## Task 2: Service — Simpan `rekam_medis` dalam `add_payment_multi()`

**Files:**
- Modify: `app/modules/beasiswa/service.py`
- Test: `app/tests/test_beasiswa_service.py`

- [ ] **Step 1: Tulis failing test dulu**

Buka `app/tests/test_beasiswa_service.py`. Tambahkan di akhir file, setelah test klaim yang sudah ada:

```python
# ── Rekam Medis dalam add_payment_multi ──────────────────────────────────────

def _add_siswa_b():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "Siti", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})

def test_add_payment_multi_saves_rekam_medis():
    """Row By Medical dengan rekam_medis → tersimpan ke tabel rekam_medis."""
    _add_siswa_b()
    rows = [{
        "siswa_code": "1250001",
        "cat1": "By Medical",
        "cat2": "Rawat Inap",
        "amount": 3200000,
        "tgl_pengajuan": "", "tgl_receive": "", "tgl_pa": "", "tgl_final": "",
        "etf_pa_line_id": None,
        "rekam_medis": {
            "kelas": "Standard/Kelas 2",
            "rumah_sakit": "RS Siloam Jakarta",
            "diagnosa": "Demam Berdarah",
            "spesialisasi": "Internal Medicine",
            "catatan": "catatan test",
        },
    }]
    result = add_payment_multi(COMPANY_ID, "ETF", "2026-06-03", "AGRI", "PT ABC", rows)
    assert result["ok"] is True
    assert result["saved"] == 1
    conn = get_conn()
    pb = conn.execute("SELECT * FROM payment_beasiswa WHERE company_id=?", (COMPANY_ID,)).fetchone()
    assert pb is not None
    rm = conn.execute("SELECT * FROM rekam_medis WHERE payment_id=?", (pb["id"],)).fetchone()
    assert rm is not None
    assert rm["kelas"] == "Standard/Kelas 2"
    assert rm["rumah_sakit"] == "RS Siloam Jakarta"
    assert rm["diagnosa"] == "Demam Berdarah"
    assert rm["spesialisasi"] == "Internal Medicine"
    assert rm["catatan"] == "catatan test"
    assert rm["siswa_code"] == "1250001"
    assert rm["company_id"] == COMPANY_ID
    conn.close()

def test_add_payment_multi_medical_missing_rekam_medis_returns_error():
    """Row By Medical tanpa rekam_medis → ditolak."""
    _add_siswa_b()
    rows = [{
        "siswa_code": "1250001",
        "cat1": "By Medical",
        "cat2": "Rawat Inap",
        "amount": 3200000,
        "tgl_pengajuan": "", "tgl_receive": "", "tgl_pa": "", "tgl_final": "",
        "etf_pa_line_id": None,
        # tidak ada rekam_medis
    }]
    result = add_payment_multi(COMPANY_ID, "ETF", "2026-06-03", "AGRI", "PT ABC", rows)
    assert result["ok"] is False
    assert "medis" in result["pesan"].lower() or "rekam" in result["pesan"].lower()

def test_add_payment_multi_medical_incomplete_rekam_medis_returns_error():
    """Row By Medical dengan rekam_medis tapi field wajib kosong → ditolak."""
    _add_siswa_b()
    rows = [{
        "siswa_code": "1250001",
        "cat1": "By Medical",
        "cat2": "Rawat Inap",
        "amount": 3200000,
        "tgl_pengajuan": "", "tgl_receive": "", "tgl_pa": "", "tgl_final": "",
        "etf_pa_line_id": None,
        "rekam_medis": {
            "kelas": "VIP",
            "rumah_sakit": "",   # kosong — wajib
            "diagnosa": "",      # kosong — wajib
            "spesialisasi": "",  # kosong — wajib
            "catatan": "",
        },
    }]
    result = add_payment_multi(COMPANY_ID, "ETF", "2026-06-03", "AGRI", "PT ABC", rows)
    assert result["ok"] is False

def test_add_payment_multi_non_medical_no_rekam_medis_ok():
    """Row non-medical tanpa rekam_medis → tetap berhasil."""
    _add_siswa_b()
    rows = [{
        "siswa_code": "1250001",
        "cat1": "By Pendidikan",
        "cat2": "Biaya Kuliah",
        "amount": 5000000,
        "tgl_pengajuan": "", "tgl_receive": "", "tgl_pa": "", "tgl_final": "",
        "etf_pa_line_id": None,
    }]
    result = add_payment_multi(COMPANY_ID, "ETF", "2026-06-03", "AGRI", "PT ABC", rows)
    assert result["ok"] is True
    conn = get_conn()
    rm_count = conn.execute("SELECT COUNT(*) FROM rekam_medis WHERE company_id=?", (COMPANY_ID,)).fetchone()[0]
    assert rm_count == 0  # tidak ada rekam_medis untuk non-medical
    conn.close()
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```bash
cd app && python -m pytest tests/test_beasiswa_service.py::test_add_payment_multi_saves_rekam_medis -v
```

Expected: `FAILED` — karena service belum insert ke `rekam_medis`.

- [ ] **Step 3: Implementasi di `add_payment_multi()`**

Buka `app/modules/beasiswa/service.py`. Cari fungsi `add_payment_multi()` (sekitar baris 322). Di dalam loop `for row in rows:`, setelah validasi amount > 0, tambah validasi rekam_medis untuk By Medical **sebelum** insert:

```python
# Validasi rekam_medis wajib untuk By Medical
_CAT2_MEDICAL = {"Rawat Jalan", "Rawat Inap"}
if row.get("cat1") == "By Medical" and row.get("cat2") in _CAT2_MEDICAL:
    rm = row.get("rekam_medis") or {}
    if not rm.get("kelas") or not rm.get("rumah_sakit") or \
       not rm.get("diagnosa") or not rm.get("spesialisasi"):
        conn.close()
        return {"ok": False,
                "pesan": "Data rekam medis wajib diisi (kelas, rumah sakit, diagnosa, spesialisasi).",
                "saved": 0}
```

Kemudian, setelah `cur = conn.execute("""INSERT INTO payment_beasiswa...""", ...)` dan `payment_ids.append(cur.lastrowid)`, tambah:

```python
# Insert rekam_medis jika By Medical
if row.get("cat1") == "By Medical" and row.get("cat2") in _CAT2_MEDICAL:
    rm = row.get("rekam_medis", {})
    conn.execute(
        """INSERT INTO rekam_medis
           (company_id, payment_id, siswa_code, kelas, rumah_sakit,
            diagnosa, spesialisasi, catatan)
           VALUES (?,?,?,?,?,?,?,?)""",
        (company_id, cur.lastrowid, siswa_code,
         rm.get("kelas", ""),       rm.get("rumah_sakit", ""),
         rm.get("diagnosa", ""),    rm.get("spesialisasi", ""),
         rm.get("catatan", "") or None)
    )
```

Pindahkan konstanta `_CAT2_MEDICAL` ke luar fungsi (level modul) agar tidak re-defined setiap iterasi:

```python
# Di level modul, sebelum fungsi add_payment_multi:
_CAT2_MEDICAL = {"Rawat Jalan", "Rawat Inap"}
```

- [ ] **Step 4: Jalankan semua test baru — pastikan PASS**

```bash
cd app && python -m pytest tests/test_beasiswa_service.py -k "rekam_medis" -v
```

Expected:
```
PASSED test_add_payment_multi_saves_rekam_medis
PASSED test_add_payment_multi_medical_missing_rekam_medis_returns_error
PASSED test_add_payment_multi_medical_incomplete_rekam_medis_returns_error
PASSED test_add_payment_multi_non_medical_no_rekam_medis_ok
```

- [ ] **Step 5: Jalankan full test suite — pastikan tidak ada regresi**

```bash
cd app && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: semua test yang ada sebelumnya tetap PASS.

- [ ] **Step 6: Commit**

```bash
git add app/modules/beasiswa/service.py app/tests/test_beasiswa_service.py
git commit -m "feat(service): save rekam_medis in add_payment_multi for By Medical rows"
```

---

## Task 3: Frontend — Sub-row Data Medis di `ipayAddRow()`

**Files:**
- Modify: `app/templates/payment_memo/index.html`

Catatan: fungsi `ipayAddRow()` ada di bagian bawah file dalam blok `<script>`. Konstanta `KELAS_MEDICAL` dan `SPESIALISASI_LIST` ditambah di blok variabel JS di atas (dekat `VENDOR_LIST`, `SISWA_LIST`).

- [ ] **Step 1: Tambah konstanta KELAS_MEDICAL dan SPESIALISASI_LIST**

Cari baris `const COMPANY_CODE = "{{ company_code }}";` di blok script. Tambah setelah baris itu:

```js
const KELAS_MEDICAL = [
  "Rawat Jalan", "Emergency", "Basic/Kelas 3", "Standard/Kelas 2",
  "Deluxe/Kelas 1", "VIP", "VVIP", "SVIP"
];
const SPESIALISASI_LIST = [
  "Internal Medicine", "Cardiology", "Orthopaedy", "Obstetric & Gynaecology",
  "Pediatrics", "Pulmonology", "Neurology", "Neurosurgeon", "General Surgery",
  "ENT", "Dermatovenerology", "Psychiatry", "Opthalmology", "Plastic Surgery",
  "General Practionist", "Dentistry"
];
```

- [ ] **Step 2: Tambah fungsi helper `_buildMedisRow(tr)`**

Tambah fungsi baru setelah fungsi `ipayUpdatePAM()`, sebelum `ipayAddRow()`:

```js
function _buildMedisRow(tr) {
  const medisRow = document.createElement("tr");
  medisRow.className = "ipay-medis-row";
  medisRow.style.display = "none"; // hidden by default
  const td = document.createElement("td");
  td.colSpan = 10;
  td.style.cssText = "padding:0 8px 10px 24px;background:#fffbeb";

  // Build selects and inputs
  function mkSel(opts, placeholder) {
    const s = document.createElement("select");
    s.style.cssText = "width:100%;border:1px solid #fcd34d;border-radius:4px;padding:5px 6px;font-size:12px;background:#fff;box-sizing:border-box";
    s.innerHTML = `<option value="">${placeholder}</option>` +
      opts.map(o => `<option value="${o}">${o}</option>`).join("");
    return s;
  }
  function mkInp(placeholder) {
    const i = document.createElement("input");
    i.type = "text"; i.placeholder = placeholder;
    i.style.cssText = "width:100%;box-sizing:border-box;border:1px solid #fcd34d;border-radius:4px;padding:5px 6px;font-size:12px;background:#fff";
    return i;
  }
  function lbl(text, required) {
    const d = document.createElement("div");
    d.style.cssText = "font-size:10px;color:#6b7280;margin-bottom:3px";
    d.innerHTML = text + (required ? ' <span style="color:#ef4444">*</span>' : "");
    return d;
  }

  const selKelas        = mkSel(KELAS_MEDICAL, "— Pilih Kelas —");
  const inpRS           = mkInp("Rumah Sakit");
  const inpDiagnosa     = mkInp("Diagnosa");
  const selSpesialisasi = mkSel(SPESIALISASI_LIST, "— Spesialisasi —");
  const inpCatatan      = mkInp("Catatan (opsional)");

  // Warning bar — shown when collapsed and incomplete
  const warnBar = document.createElement("div");
  warnBar.style.cssText = "display:none;background:#fef2f2;border:1px dashed #fca5a5;border-radius:4px;padding:6px 10px;font-size:12px;color:#b91c1c;margin-bottom:4px";
  warnBar.textContent = "⚠️ Data Medis belum diisi — klik ▲ untuk expand dan isi data";
  tr._medisWarn = warnBar;

  const grid = document.createElement("div");
  grid.style.cssText = "display:grid;grid-template-columns:1fr 1.5fr 1.5fr 1.5fr;gap:8px;margin-bottom:8px";

  function field(labelText, el, required) {
    const w = document.createElement("div");
    w.appendChild(lbl(labelText, required)); w.appendChild(el); return w;
  }
  grid.appendChild(field("Kelas", selKelas, true));
  grid.appendChild(field("Rumah Sakit", inpRS, true));
  grid.appendChild(field("Diagnosa", inpDiagnosa, true));
  grid.appendChild(field("Spesialisasi", selSpesialisasi, true));

  const catRow = document.createElement("div");
  catRow.appendChild(lbl("Catatan", false)); catRow.appendChild(inpCatatan);

  const inner = document.createElement("div");
  inner.style.cssText = "background:#fff8ed;border:1px dashed #f59e0b;border-radius:6px;padding:10px 12px";
  const title = document.createElement("div");
  title.style.cssText = "font-size:10px;font-weight:700;color:#b45309;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px";
  title.textContent = "📋 Data Medis — Wajib diisi";
  inner.appendChild(title); inner.appendChild(grid); inner.appendChild(catRow);
  td.appendChild(warnBar); td.appendChild(inner);
  medisRow.appendChild(td);

  // Expose refs on tr
  tr._medisRow    = medisRow;
  tr._medisSelKelas        = selKelas;
  tr._medisInpRS           = inpRS;
  tr._medisInpDiagnosa     = inpDiagnosa;
  tr._medisSelSpesialisasi = selSpesialisasi;
  tr._medisInpCatatan      = inpCatatan;

  // Helper: read current data
  tr._getMedisData = () => ({
    kelas:        selKelas.value,
    rumah_sakit:  inpRS.value.trim(),
    diagnosa:     inpDiagnosa.value.trim(),
    spesialisasi: selSpesialisasi.value,
    catatan:      inpCatatan.value.trim(),
  });

  // Helper: check complete
  tr._medisComplete = () => {
    const m = tr._getMedisData();
    return !!(m.kelas && m.rumah_sakit && m.diagnosa && m.spesialisasi);
  };

  return medisRow;
}

function _isMedical(cat1, cat2) {
  return cat1 === "By Medical" && (cat2 === "Rawat Jalan" || cat2 === "Rawat Inap");
}
```

- [ ] **Step 3: Modifikasi `ipayAddRow()` — insert medisRow setelah tr, tambah toggle button**

Di dalam `ipayAddRow()`, cari baris `tr._cat1Select = sCat1;`. Setelah semua setup row selesai (sebelum `document.getElementById("ipay-tbody").appendChild(tr)`), tambah:

```js
// Build medis sub-row
const medisRow = _buildMedisRow(tr);

// Toggle button — ganti btnDel setup agar ada tombol ▲/▼ sebelumnya
// Tambah toggle btn di tdDel (sebelum btnDel)
const btnToggle = document.createElement("button");
btnToggle.className = "btn btn-sm";
btnToggle.style.cssText = "background:#f59e0b;color:#fff;padding:2px 7px;display:none";
btnToggle.textContent = "▲";
btnToggle.title = "Toggle Data Medis";
btnToggle.addEventListener("click", () => {
  const expanded = medisRow.style.display !== "none";
  medisRow.style.display = expanded ? "none" : "";
  btnToggle.textContent = expanded ? "▼" : "▲";
  // Update warning bar saat collapse
  if (expanded && !tr._medisComplete()) {
    tr._medisWarn.style.display = "block";
  } else {
    tr._medisWarn.style.display = "none";
  }
});
tr._medisBtnToggle = btnToggle;
tdDel.insertBefore(btnToggle, btnDel);
```

Ubah event listener di cat1 `sCat1.addEventListener("change", ...)` — di bagian akhir handler (setelah `ipayUpdateTotal()` dan `_ipayUpdateSisaCell(tr)`), tambah:

```js
// Show/hide medis row berdasarkan cat1
const cat2val = tr._cat2Drop._hid.value;
const isMed = _isMedical(sCat1.value, cat2val);
medisRow.style.display = isMed ? "" : "none";
btnToggle.style.display = isMed ? "" : "none";
btnToggle.textContent = "▲";
if (!isMed) {
  // Reset medis fields saat tidak lagi By Medical
  tr._medisSelKelas.value = "";
  tr._medisInpRS.value = "";
  tr._medisInpDiagnosa.value = "";
  tr._medisSelSpesialisasi.value = "";
  tr._medisInpCatatan.value = "";
  tr._medisWarn.style.display = "none";
}
```

Juga pasang listener di cat2 dropdown. Setelah `_mkDrop()` menghasilkan `cat2Drop`, tambah watcher dengan cara override `_hid` value change. Karena `_mkDrop` menggunakan `mousedown` event untuk set `hid.value`, bungkus dengan MutationObserver **atau** cara yang lebih sederhana: gunakan custom event. Pendekatan paling simpel — di dalam `_mkDrop`, setelah `hid.value = c`, dispatch event:

Cari fungsi `_mkDrop` di file yang sama, temukan baris:
```js
d.addEventListener("mousedown", () => { hid.value = c; lbl.textContent = c; ...
```
Ubah menjadi:
```js
d.addEventListener("mousedown", () => {
  hid.value = c; lbl.textContent = c; lbl.style.color = "#111827"; pan.style.display = "none";
  hid.dispatchEvent(new Event("change"));
});
```

Kemudian di `ipayAddRow()`, setelah membuat `cat2Drop`, tambah listener:

```js
cat2Drop._hid.addEventListener("change", () => {
  const isMed = _isMedical(sCat1.value, cat2Drop._hid.value);
  medisRow.style.display = isMed ? "" : "none";
  btnToggle.style.display = isMed ? "" : "none";
  btnToggle.textContent = "▲";
  if (!isMed) {
    tr._medisSelKelas.value = "";
    tr._medisInpRS.value = "";
    tr._medisInpDiagnosa.value = "";
    tr._medisSelSpesialisasi.value = "";
    tr._medisInpCatatan.value = "";
    tr._medisWarn.style.display = "none";
  }
});
```

Akhirnya, setelah `document.getElementById("ipay-tbody").appendChild(tr)`, tambah:

```js
// Insert medisRow tepat setelah tr
document.getElementById("ipay-tbody").insertBefore(medisRow, tr.nextSibling);
```

Juga update btnDel listener untuk juga remove medisRow:
```js
// Di dalam btnDel addEventListener("click", ...) — setelah sugg.remove():
medisRow.remove();
```

- [ ] **Step 4: Verifikasi manual di browser**

Buka http://localhost:5050/payment-memo, login, masuk tab Input Payment.
1. Klik "+ Tambah Baris"
2. Pilih siswa → cat1 dropdown muncul
3. Pilih "By Medical" sebagai cat1 → pastikan cat2 dropdown muncul
4. Pilih "Rawat Inap" sebagai cat2 → **section Data Medis harus auto-expand** di bawah row
5. Isi semua field, ganti cat2 ke bukan Rawat Jalan/Inap → section harus hilang
6. Ganti kembali ke Rawat Inap → section muncul lagi (field kosong)
7. Klik tombol ▲ → section collapse, muncul warning merah karena belum diisi

- [ ] **Step 5: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat(ui): add Data Medis expand section in Input Payment for By Medical rows"
```

---

## Task 4: Frontend — Validasi di `ipaySave()`

**Files:**
- Modify: `app/templates/payment_memo/index.html`

- [ ] **Step 1: Update `ipaySave()` — validasi dan kirim rekam_medis**

Cari fungsi `ipaySave()`. Setelah blok validasi `overBudget`, tambah validasi Data Medis:

```js
// Validasi Data Medis untuk row By Medical
const incompleteMedis = allTrs.filter(tr => {
  const cat1 = tr._cat1Select?.value;
  const cat2 = tr._cat2Drop?._hid?.value;
  const amt  = parseFloat(tr._amtInp?.value) || 0;
  return amt > 0 && _isMedical(cat1, cat2) && !tr._medisComplete();
});
if (incompleteMedis.length) {
  // Expand dan highlight semua row yang belum lengkap
  incompleteMedis.forEach(tr => {
    if (tr._medisRow) {
      tr._medisRow.style.display = "";
      tr._medisBtnToggle.textContent = "▲";
    }
    if (tr._medisWarn) tr._medisWarn.style.display = "block";
  });
  showToast(`${incompleteMedis.length} row By Medical belum mengisi Data Medis.`, "error");
  return;
}
```

Kemudian di bagian build `rows`, ubah `.map(tr => ({...}))` agar include `rekam_medis`:

```js
const rows = allTrs.map(tr => {
  const cat1 = tr._cat1Select.value;
  const cat2 = tr._cat2Drop._hid.value;
  const row = {
    siswa_code:     tr.dataset.siswaCode || "",
    cat1,
    cat2,
    amount:         parseFloat(tr._amtInp.value) || 0,
    tgl_pengajuan:  tr._tgls[0].value,
    tgl_receive:    tr._tgls[1].value,
    tgl_pa:         tr._tgls[2].value,
    tgl_final:      tr._tgls[3].value,
    etf_pa_line_id: tr._hidEtfLineId?.value ? parseInt(tr._hidEtfLineId.value) : null,
  };
  if (_isMedical(cat1, cat2)) {
    row.rekam_medis = tr._getMedisData();
  }
  return row;
}).filter(r => r.amount > 0);
```

- [ ] **Step 2: Test end-to-end di browser**

1. Buka Input Payment, tambah row By Medical (Rawat Inap), **jangan isi Data Medis**
2. Klik "💾 Simpan Payment" → harus muncul toast error + section expand + warning merah
3. Isi semua field Data Medis (Kelas, RS, Diagnosa, Spesialisasi)
4. Klik "💾 Simpan Payment" → harus berhasil (toast success)
5. Cek di DB: `SELECT * FROM rekam_medis` harus ada 1 record

```bash
python -c "
import sys; sys.path.insert(0,'app')
import config; config.DB_PATH='app/finance_hub.db'
from database import get_conn
c = get_conn()
print(c.execute('SELECT * FROM rekam_medis').fetchall())
"
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat(ui): validate and submit rekam_medis in ipaySave"
```

---

## Task 5: Hapus `rekam_medis` saat `payment_beasiswa` dihapus

**Files:**
- Modify: `app/modules/beasiswa/service.py`
- Test: `app/tests/test_beasiswa_service.py`

- [ ] **Step 1: Tulis failing test**

Tambah di `test_beasiswa_service.py`:

```python
def test_delete_payment_juga_hapus_rekam_medis():
    """Hapus payment_beasiswa By Medical → rekam_medis ikut terhapus."""
    _add_siswa_b()
    rows = [{
        "siswa_code": "1250001", "cat1": "By Medical", "cat2": "Rawat Inap",
        "amount": 3200000, "tgl_pengajuan": "", "tgl_receive": "", "tgl_pa": "", "tgl_final": "",
        "etf_pa_line_id": None,
        "rekam_medis": {
            "kelas": "VIP", "rumah_sakit": "RS ABC",
            "diagnosa": "Flu", "spesialisasi": "General Practionist", "catatan": "",
        },
    }]
    add_payment_multi(COMPANY_ID, "ETF", "2026-06-03", "AGRI", "PT ABC", rows)
    conn = get_conn()
    pb = conn.execute("SELECT id FROM payment_beasiswa WHERE company_id=?", (COMPANY_ID,)).fetchone()
    pay_id = pb["id"]
    rm_before = conn.execute("SELECT id FROM rekam_medis WHERE payment_id=?", (pay_id,)).fetchone()
    assert rm_before is not None
    conn.close()

    from modules.beasiswa.service import delete_payment_beasiswa
    result = delete_payment_beasiswa(pay_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    rm_after = conn.execute("SELECT id FROM rekam_medis WHERE payment_id=?", (pay_id,)).fetchone()
    assert rm_after is None  # harus sudah terhapus
    conn.close()
```

- [ ] **Step 2: Jalankan — pastikan FAIL**

```bash
cd app && python -m pytest tests/test_beasiswa_service.py::test_delete_payment_juga_hapus_rekam_medis -v
```

- [ ] **Step 3: Cari fungsi `delete_payment_beasiswa` dan tambah delete cascade**

Cari `def delete_payment_beasiswa` di `service.py`. Sebelum (atau bersamaan dengan) `DELETE FROM payment_beasiswa WHERE id=...`, tambah:

```python
conn.execute(
    "DELETE FROM rekam_medis WHERE payment_id=? AND company_id=?",
    (payment_id, company_id)
)
```

- [ ] **Step 4: Jalankan full test suite**

```bash
cd app && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: semua PASS.

- [ ] **Step 5: Commit**

```bash
git add app/modules/beasiswa/service.py app/tests/test_beasiswa_service.py
git commit -m "feat(service): cascade delete rekam_medis when payment_beasiswa is deleted"
```

---

## Self-Review

**Spec coverage:**
- ✅ Tabel baru `rekam_medis` — Task 1
- ✅ Auto-expand saat By Medical + cat2 — Task 3
- ✅ Toggle ▲/▼ manual — Task 3
- ✅ Warning state saat collapse sebelum diisi — Task 3
- ✅ 4 field wajib + 1 opsional — Task 3 & 4
- ✅ Validasi frontend (ditolak + highlight) — Task 4
- ✅ Validasi backend safeguard — Task 2
- ✅ Simpan dalam satu transaksi — Task 2 (existing try/except di `add_payment_multi`)
- ✅ Cascade delete — Task 5
- ✅ Row non-medical tidak terpengaruh — Task 2 test + Task 3 behavior

**Placeholder scan:** Tidak ada TBD/TODO.

**Type consistency:** `tr._getMedisData()` defined Task 3 → used Task 4. `_isMedical()` defined Task 3 → used Task 3 & 4. `_CAT2_MEDICAL` di service.py level modul → used dalam loop Task 2. Semua konsisten.
