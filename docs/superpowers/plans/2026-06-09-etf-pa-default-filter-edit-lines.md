# ETF PA Default Filter + Edit Line Fields — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) ETF PA halaman default filter Open+On Process; (2) modal edit bisa edit field per-line siswa (Jenis Bayar, Semester, Tahun Ajaran, IPK Sblmnya, Jumlah).

**Architecture:** Service `get_pa_flat` diperluas untuk `status_filter="active"` (SQL IN clause); route default `sf="active"`; `update_pa` diperluas untuk juga update `lines_tbl` jika `line_id` ada di payload; template dropdown + `data-line-id` + modal fields baru + JS `openEditById/saveEdit` diperluas.

**Tech Stack:** Flask (Python), SQLite, vanilla JS inline di Jinja2 template.

---

## File Map

| File | Perubahan |
|------|-----------|
| `app/modules/etf_payment_application/service.py` | `get_pa_flat`: cabang "active"; `update_pa`: unpack `lines_tbl`, tambah UPDATE lines |
| `app/modules/etf_payment_application/routes.py` | Default `sf="active"`, validasi tambah `"active"` |
| `app/templates/etf_payment_application/index.html` | Dropdown filter; `data-line-id` + tombol Edit; hidden input + 5 field baru di modal; update `openEditById` dan `saveEdit` |
| `tests/test_etf_pa.py` | Test baru: `get_pa_flat` active filter + `update_pa` line update |

---

## Task 1 — Backend: active filter + update_pa line fields + route default

**Files:**
- Modify: `app/modules/etf_payment_application/service.py`
- Modify: `app/modules/etf_payment_application/routes.py`
- Create: `tests/test_etf_pa.py`

- [ ] **Step 1: Buat test file baru `tests/test_etf_pa.py`**

```python
# tests/test_etf_pa.py
import sqlite3 as _sq
import pytest


def _make_db(path):
    conn = _sq.connect(path)
    conn.execute("""
        CREATE TABLE siswa (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            code TEXT,
            nama TEXT,
            status TEXT,
            universitas TEXT,
            angkatan INTEGER,
            angkatan_kuliah TEXT,
            jenjang TEXT,
            program TEXT,
            fakultas TEXT,
            prodi TEXT,
            ipk_sem1 REAL, ipk_sem2 REAL, ipk_sem3 REAL, ipk_sem4 REAL,
            ipk_sem5 REAL, ipk_sem6 REAL, ipk_sem7 REAL, ipk_sem8 REAL,
            ipk_sem9 REAL, ipk_sem10 REAL
        )
    """)
    conn.execute("""
        CREATE TABLE etf_pa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            pa_number TEXT,
            tgl_payment_application TEXT,
            tgl_surat_pengajuan TEXT,
            doc_received_by_educ TEXT,
            received_pa_from_educ TEXT,
            checked_by_fincon TEXT,
            approved_by_htj_1 TEXT,
            send_pa_back_to_educ TEXT,
            pa_received_by_po_fin TEXT,
            approval_by_htj_2 TEXT,
            nomor_pam TEXT,
            tanggal_bayar TEXT,
            keterangan TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE etf_pa_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pa_id INTEGER,
            student_id INTEGER,
            jenis_pembayaran TEXT,
            semester TEXT,
            tahun_ajaran TEXT,
            ipk_sem_sebelumnya REAL DEFAULT 0,
            jumlah_pembayaran REAL DEFAULT 0
        )
    """)
    # Seed: 1 siswa, 3 PA with different statuses
    conn.execute("INSERT INTO siswa VALUES (1,1,'S001','Budi','active','Univ A',2020,'2020',\
'S1','Teknik','FT','IF',3.5,3.6,0,0,0,0,0,0,0,0)")
    conn.execute("INSERT INTO etf_pa (id,company_id,pa_number,status,created_at) VALUES (1,1,'PA/ETF/001/2026','open','2026-01-01')")
    conn.execute("INSERT INTO etf_pa (id,company_id,pa_number,status,created_at) VALUES (2,1,'PA/ETF/002/2026','on_process','2026-01-02')")
    conn.execute("INSERT INTO etf_pa (id,company_id,pa_number,status,created_at) VALUES (3,1,'PA/ETF/003/2026','complete','2026-01-03')")
    conn.execute("INSERT INTO etf_pa_lines (pa_id,student_id,jenis_pembayaran,semester,tahun_ajaran,jumlah_pembayaran) VALUES (1,1,'UKT','1','2024/2025',5000000)")
    conn.execute("INSERT INTO etf_pa_lines (pa_id,student_id,jenis_pembayaran,semester,tahun_ajaran,jumlah_pembayaran) VALUES (2,1,'UKT','2','2024/2025',5000000)")
    conn.execute("INSERT INTO etf_pa_lines (pa_id,student_id,jenis_pembayaran,semester,tahun_ajaran,jumlah_pembayaran) VALUES (3,1,'UKT','3','2024/2025',5000000)")
    conn.commit()
    conn.close()
    return path


def _fake_conn_factory(db_path):
    def _fake():
        c = _sq.connect(db_path)
        c.row_factory = _sq.Row
        return c
    return _fake


def test_get_pa_flat_active_returns_open_and_on_process(monkeypatch, tmp_path):
    db_path = str(tmp_path / "t.db")
    _make_db(db_path)
    import app.database as db_mod
    monkeypatch.setattr(db_mod, "get_conn", _fake_conn_factory(db_path))
    from app.modules.etf_payment_application.service import get_pa_flat
    rows = get_pa_flat(1, "agri", "active")
    statuses = {r["status"] for r in rows}
    assert "open" in statuses
    assert "on_process" in statuses
    assert "complete" not in statuses


def test_get_pa_flat_active_excludes_complete(monkeypatch, tmp_path):
    db_path = str(tmp_path / "t.db")
    _make_db(db_path)
    import app.database as db_mod
    monkeypatch.setattr(db_mod, "get_conn", _fake_conn_factory(db_path))
    from app.modules.etf_payment_application.service import get_pa_flat
    rows = get_pa_flat(1, "agri", "active")
    assert all(r["status"] != "complete" for r in rows)


def test_get_pa_flat_no_filter_returns_all(monkeypatch, tmp_path):
    db_path = str(tmp_path / "t.db")
    _make_db(db_path)
    import app.database as db_mod
    monkeypatch.setattr(db_mod, "get_conn", _fake_conn_factory(db_path))
    from app.modules.etf_payment_application.service import get_pa_flat
    rows = get_pa_flat(1, "agri", "")
    statuses = {r["status"] for r in rows}
    assert statuses == {"open", "on_process", "complete"}


def test_update_pa_updates_line_fields(monkeypatch, tmp_path):
    db_path = str(tmp_path / "t.db")
    _make_db(db_path)
    import app.database as db_mod
    monkeypatch.setattr(db_mod, "get_conn", _fake_conn_factory(db_path))
    from app.modules.etf_payment_application.service import update_pa

    # Get the line_id of PA 1
    conn = _sq.connect(db_path)
    line_id = conn.execute("SELECT id FROM etf_pa_lines WHERE pa_id=1").fetchone()[0]
    conn.close()

    result = update_pa(1, 1, {
        "tgl_payment_application": "2026-06-01",
        "tgl_surat_pengajuan": "",
        "doc_received_by_educ": "",
        "received_pa_from_educ": "",
        "checked_by_fincon": "",
        "approved_by_htj_1": "",
        "send_pa_back_to_educ": "",
        "pa_received_by_po_fin": "",
        "approval_by_htj_2": "",
        "nomor_pam": "",
        "tanggal_bayar": "",
        "keterangan": "",
        "status": "open",
        "line_id": line_id,
        "jenis_pembayaran": "Biaya Hidup",
        "semester": "3",
        "tahun_ajaran": "2025/2026",
        "ipk_sem_sebelumnya": 3.75,
        "jumlah_pembayaran": 9999999,
    }, "agri")

    assert result["ok"] is True

    conn2 = _sq.connect(db_path)
    line = conn2.execute("SELECT * FROM etf_pa_lines WHERE id=?", (line_id,)).fetchone()
    conn2.close()
    assert line[3] == "Biaya Hidup"   # jenis_pembayaran
    assert line[4] == "3"             # semester
    assert line[5] == "2025/2026"     # tahun_ajaran
    assert float(line[6]) == 3.75     # ipk_sem_sebelumnya
    assert float(line[7]) == 9999999  # jumlah_pembayaran
```

- [ ] **Step 2: Jalankan — pastikan FAIL (ImportError)**

```
cd C:\Financehub && python -m pytest tests/test_etf_pa.py -v
```

Expected: `FAILED` — `cannot import name 'get_pa_flat'` atau test logic fail karena "active" belum didukung.

- [ ] **Step 3: Update `get_pa_flat` di `app/modules/etf_payment_application/service.py`**

Cari (lines 95–99):
```python
    extra_where = ""
    params: list = [company_id]
    if status_filter:
        extra_where = " AND LOWER(p.status)=?"
        params.append(status_filter.lower())
```

Ganti dengan:
```python
    extra_where = ""
    params: list = [company_id]
    if status_filter == "active":
        extra_where = " AND LOWER(p.status) IN ('open', 'on_process')"
    elif status_filter:
        extra_where = " AND LOWER(p.status)=?"
        params.append(status_filter.lower())
```

- [ ] **Step 4: Update `update_pa` — unpack `lines_tbl` + tambah line UPDATE**

Cari line 370:
```python
    pa_tbl, _, _, pam_prefix = _tbls(tab)
```
Ganti dengan:
```python
    pa_tbl, lines_tbl, _, pam_prefix = _tbls(tab)
```

Cari (lines 421–422 — setelah `conn.execute(UPDATE pa_tbl...)` dan sebelum `conn.commit()`):
```python
    conn.commit()
    conn.close()
```

Sisipkan sebelum `conn.commit()`:
```python
    line_id = data.get("line_id")
    if line_id:
        conn.execute(
            f"""UPDATE {lines_tbl} SET
                 jenis_pembayaran   = ?,
                 semester           = ?,
                 tahun_ajaran       = ?,
                 ipk_sem_sebelumnya = ?,
                 jumlah_pembayaran  = ?
                WHERE id=? AND pa_id=?""",
            (data.get("jenis_pembayaran", ""),
             data.get("semester", ""),
             data.get("tahun_ajaran", ""),
             data.get("ipk_sem_sebelumnya") or 0,
             data.get("jumlah_pembayaran") or 0,
             line_id, pa_id)
        )
```

- [ ] **Step 5: Update route default di `app/modules/etf_payment_application/routes.py`**

Cari (lines 41–43):
```python
    sf = request.args.get("sf", "").lower()
    if sf not in ("open", "on_process", "complete"):
        sf = ""
```

Ganti dengan:
```python
    sf = request.args.get("sf", "active").lower()
    if sf not in ("open", "on_process", "complete", "active", ""):
        sf = "active"
```

- [ ] **Step 6: Jalankan semua test — pastikan 4 test baru + 6 existing PASS**

```
cd C:\Financehub && python -m pytest tests/ -v
```

Expected: 10 passed total (6 existing + 4 new).

- [ ] **Step 7: Commit**

```bash
git add app/modules/etf_payment_application/service.py app/modules/etf_payment_application/routes.py tests/test_etf_pa.py
git commit -m "feat: add active filter to ETF PA and update_pa line fields support"
```

---

## Task 2 — Template HTML: dropdown + data-line-id + modal fields

**Files:**
- Modify: `app/templates/etf_payment_application/index.html`

- [ ] **Step 1: Update dropdown filter status (lines 177–182)**

Cari:
```html
    <select id="f-status" onchange="statusFilterChanged(this)" style="font-size:.82rem">
      <option value="">Semua</option>
      <option value="open" {% if active_sf == 'open' %}selected{% endif %}>Open</option>
      <option value="on_process" {% if active_sf == 'on_process' %}selected{% endif %}>On Process</option>
      <option value="complete" {% if active_sf == 'complete' %}selected{% endif %}>Complete</option>
    </select>
```

Ganti dengan:
```html
    <select id="f-status" onchange="statusFilterChanged(this)" style="font-size:.82rem">
      <option value="">Semua</option>
      <option value="active" {% if active_sf == 'active' %}selected{% endif %}>Open + On Process</option>
      <option value="open" {% if active_sf == 'open' %}selected{% endif %}>Open</option>
      <option value="on_process" {% if active_sf == 'on_process' %}selected{% endif %}>On Process</option>
      <option value="complete" {% if active_sf == 'complete' %}selected{% endif %}>Complete</option>
    </select>
```

- [ ] **Step 2: Tambah `data-line-id` ke `<tr>` (line 326)**

Cari:
```html
      <tr data-pa-id="{{ r.pa_id }}"
          data-nama="{{ r.nama | lower }}"
```

Ganti dengan:
```html
      <tr data-pa-id="{{ r.pa_id }}"
          data-line-id="{{ r.line_id }}"
          data-nama="{{ r.nama | lower }}"
```

- [ ] **Step 3: Update tombol Edit untuk pass `line_id` (line 370)**

Cari:
```html
        <td><button class="btn btn-primary btn-sm" onclick="openEditById({{ r.pa_id }})">Edit</button></td>
```

Ganti dengan:
```html
        <td><button class="btn btn-primary btn-sm" onclick="openEditById({{ r.pa_id }}, {{ r.line_id }})">Edit</button></td>
```

- [ ] **Step 4: Tambah hidden input `edit-line-id` di modal (setelah baris 414)**

Cari:
```html
    <input type="hidden" id="edit-pa-id">
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:.75rem">
```

Ganti dengan:
```html
    <input type="hidden" id="edit-pa-id">
    <input type="hidden" id="edit-line-id">
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:.75rem">
```

- [ ] **Step 5: Tambah 5 field baru di modal — setelah `edit-keterangan` dan sebelum tombol Batal/Simpan (line 435–439)**

Cari:
```html
    <div class="form-group"><label>Keterangan</label><textarea id="edit-keterangan" rows="3" style="width:100%; resize:vertical"></textarea></div>
    <div style="display:flex; gap:.75rem; justify-content:flex-end; margin-top:1rem">
      <button class="btn btn-secondary" onclick="closeModal('modal-edit-pa')">Batal</button>
      <button class="btn btn-primary" onclick="saveEdit()">Simpan</button>
    </div>
```

Ganti dengan:
```html
    <div class="form-group"><label>Keterangan</label><textarea id="edit-keterangan" rows="3" style="width:100%; resize:vertical"></textarea></div>
    <div style="border-top:1px solid var(--border);margin-top:.75rem;padding-top:.75rem">
      <div style="font-size:.75rem;font-weight:600;color:#374151;margin-bottom:.5rem">Data Siswa (Line)</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem">
        <div class="form-group"><label>Jenis Bayar</label>
          <select id="edit-jenis-bayar">
            <option value="">-- Pilih --</option>
            {% for c in cat1 %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
          </select>
        </div>
        <div class="form-group"><label>Semester</label>
          <select id="edit-semester">
            <option value="">-- Pilih --</option>
            {% for c in cat2_sem %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
          </select>
        </div>
        <div class="form-group"><label>Tahun Ajaran</label>
          <input type="text" id="edit-tahun-ajaran" placeholder="2024/2025">
        </div>
        <div class="form-group"><label>IPK Sblmnya</label>
          <input type="number" id="edit-ipk" step="0.01" min="0" max="4">
        </div>
      </div>
      <div class="form-group"><label>Jumlah (Rp)</label>
        <input type="number" id="edit-jumlah" min="0">
      </div>
    </div>
    <div style="display:flex; gap:.75rem; justify-content:flex-end; margin-top:1rem">
      <button class="btn btn-secondary" onclick="closeModal('modal-edit-pa')">Batal</button>
      <button class="btn btn-primary" onclick="saveEdit()">Simpan</button>
    </div>
```

- [ ] **Step 6: Jalankan test suite untuk pastikan tidak ada regresi**

```
cd C:\Financehub && python -m pytest tests/ -v
```

Expected: 10 passed.

- [ ] **Step 7: Commit**

```bash
git add app/templates/etf_payment_application/index.html
git commit -m "feat: add line fields to ETF PA edit modal and default active filter in dropdown"
```

---

## Task 3 — Template JS: openEditById + saveEdit

**Files:**
- Modify: `app/templates/etf_payment_application/index.html` (JS section ~lines 759–802)

- [ ] **Step 1: Ganti fungsi `openEditById` (lines 760–780)**

Cari:
```javascript
async function openEditById(paId) {
  const resp = await apiFetch(`/etf-payment-application/${paId}/header?tab=${ACTIVE_TAB}`);
  if (!resp.ok) { showToast("Gagal memuat data PA.", "error"); return; }
  const pa = await resp.json();
  document.getElementById("edit-pa-id").value       = pa.id;
  document.getElementById("edit-pa-title").textContent = `Edit PA: ${pa.pa_number}`;
  document.getElementById("edit-tgl-app").value     = pa.tgl_payment_application || "";
  document.getElementById("edit-tgl-surat").value   = pa.tgl_surat_pengajuan || "";
  document.getElementById("edit-doc-recv").value    = pa.doc_received_by_educ || "";
  document.getElementById("edit-recv-pa").value     = pa.received_pa_from_educ || "";
  document.getElementById("edit-checked").value     = pa.checked_by_fincon || "";
  document.getElementById("edit-approved1").value   = pa.approved_by_htj_1 || "";
  document.getElementById("edit-send-back").value   = pa.send_pa_back_to_educ || "";
  document.getElementById("edit-recv-po").value     = pa.pa_received_by_po_fin || "";
  document.getElementById("edit-approval2").value   = pa.approval_by_htj_2 || "";
  document.getElementById("edit-nomor-pam").value   = pa.nomor_pam || "";
  document.getElementById("edit-tgl-bayar").value   = pa.tanggal_bayar || "";
  document.getElementById("edit-keterangan").value  = pa.keterangan || "";
  document.getElementById("edit-status").value      = pa.status || "open";
  openModal("modal-edit-pa");
}
```

Ganti dengan:
```javascript
async function openEditById(paId, lineId) {
  const resp = await apiFetch(`/etf-payment-application/${paId}/header?tab=${ACTIVE_TAB}`);
  if (!resp.ok) { showToast("Gagal memuat data PA.", "error"); return; }
  const pa = await resp.json();
  document.getElementById("edit-pa-id").value          = pa.id;
  document.getElementById("edit-line-id").value         = lineId || "";
  document.getElementById("edit-pa-title").textContent  = `Edit PA: ${pa.pa_number}`;
  document.getElementById("edit-tgl-app").value         = pa.tgl_payment_application || "";
  document.getElementById("edit-tgl-surat").value       = pa.tgl_surat_pengajuan || "";
  document.getElementById("edit-doc-recv").value        = pa.doc_received_by_educ || "";
  document.getElementById("edit-recv-pa").value         = pa.received_pa_from_educ || "";
  document.getElementById("edit-checked").value         = pa.checked_by_fincon || "";
  document.getElementById("edit-approved1").value       = pa.approved_by_htj_1 || "";
  document.getElementById("edit-send-back").value       = pa.send_pa_back_to_educ || "";
  document.getElementById("edit-recv-po").value         = pa.pa_received_by_po_fin || "";
  document.getElementById("edit-approval2").value       = pa.approval_by_htj_2 || "";
  document.getElementById("edit-nomor-pam").value       = pa.nomor_pam || "";
  document.getElementById("edit-tgl-bayar").value       = pa.tanggal_bayar || "";
  document.getElementById("edit-keterangan").value      = pa.keterangan || "";
  document.getElementById("edit-status").value          = pa.status || "open";
  const lineResp = await apiFetch(`/etf-payment-application/${paId}/lines?tab=${ACTIVE_TAB}`);
  if (lineResp && lineResp.ok) {
    const lines = await lineResp.json();
    const line = lines.find(l => l.id === lineId);
    if (line) {
      document.getElementById("edit-jenis-bayar").value  = line.jenis_pembayaran || "";
      document.getElementById("edit-semester").value     = line.semester || "";
      document.getElementById("edit-tahun-ajaran").value = line.tahun_ajaran || "";
      document.getElementById("edit-ipk").value          = line.ipk_sem_sebelumnya || "";
      document.getElementById("edit-jumlah").value       = line.jumlah_pembayaran || "";
    }
  }
  openModal("modal-edit-pa");
}
```

- [ ] **Step 2: Ganti fungsi `saveEdit` (lines 781–802)**

Cari:
```javascript
async function saveEdit() {
  const paId = document.getElementById("edit-pa-id").value;
  const payload = {
    tgl_payment_application: document.getElementById("edit-tgl-app").value,
    tgl_surat_pengajuan:     document.getElementById("edit-tgl-surat").value,
    doc_received_by_educ:    document.getElementById("edit-doc-recv").value,
    received_pa_from_educ:   document.getElementById("edit-recv-pa").value,
    checked_by_fincon:       document.getElementById("edit-checked").value,
    approved_by_htj_1:       document.getElementById("edit-approved1").value,
    send_pa_back_to_educ:    document.getElementById("edit-send-back").value,
    pa_received_by_po_fin:   document.getElementById("edit-recv-po").value,
    approval_by_htj_2:       document.getElementById("edit-approval2").value,
    nomor_pam:               document.getElementById("edit-nomor-pam").value,
    tanggal_bayar:           document.getElementById("edit-tgl-bayar").value,
    keterangan:              document.getElementById("edit-keterangan").value,
    status:                  document.getElementById("edit-status").value,
  };
  const resp = await apiFetch(`/etf-payment-application/${paId}/update?tab=${ACTIVE_TAB}`, { method: "POST", body: JSON.stringify(payload) });
  const data = await resp.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) { closeModal("modal-edit-pa"); setTimeout(() => location.reload(), 800); }
}
```

Ganti dengan:
```javascript
async function saveEdit() {
  const paId = document.getElementById("edit-pa-id").value;
  const payload = {
    tgl_payment_application: document.getElementById("edit-tgl-app").value,
    tgl_surat_pengajuan:     document.getElementById("edit-tgl-surat").value,
    doc_received_by_educ:    document.getElementById("edit-doc-recv").value,
    received_pa_from_educ:   document.getElementById("edit-recv-pa").value,
    checked_by_fincon:       document.getElementById("edit-checked").value,
    approved_by_htj_1:       document.getElementById("edit-approved1").value,
    send_pa_back_to_educ:    document.getElementById("edit-send-back").value,
    pa_received_by_po_fin:   document.getElementById("edit-recv-po").value,
    approval_by_htj_2:       document.getElementById("edit-approval2").value,
    nomor_pam:               document.getElementById("edit-nomor-pam").value,
    tanggal_bayar:           document.getElementById("edit-tgl-bayar").value,
    keterangan:              document.getElementById("edit-keterangan").value,
    status:                  document.getElementById("edit-status").value,
    line_id:                 parseInt(document.getElementById("edit-line-id").value) || null,
    jenis_pembayaran:        document.getElementById("edit-jenis-bayar").value,
    semester:                document.getElementById("edit-semester").value,
    tahun_ajaran:            document.getElementById("edit-tahun-ajaran").value,
    ipk_sem_sebelumnya:      parseFloat(document.getElementById("edit-ipk").value) || 0,
    jumlah_pembayaran:       parseFloat(document.getElementById("edit-jumlah").value) || 0,
  };
  const resp = await apiFetch(`/etf-payment-application/${paId}/update?tab=${ACTIVE_TAB}`, { method: "POST", body: JSON.stringify(payload) });
  const data = await resp.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) { closeModal("modal-edit-pa"); setTimeout(() => location.reload(), 800); }
}
```

- [ ] **Step 3: Jalankan test suite**

```
cd C:\Financehub && python -m pytest tests/ -v
```

Expected: 10 passed.

- [ ] **Step 4: Commit**

```bash
git add app/templates/etf_payment_application/index.html
git commit -m "feat: update openEditById and saveEdit to load and save line fields"
```

---

## Self-Review

**Spec coverage:**
- ✅ Default filter `sf="active"` di route (Task 1 Step 5)
- ✅ `get_pa_flat` "active" → SQL IN ('open','on_process') (Task 1 Step 3)
- ✅ Dropdown "Open + On Process" di template (Task 2 Step 1)
- ✅ `data-line-id` di `<tr>` (Task 2 Step 2)
- ✅ Tombol Edit pass `line_id` (Task 2 Step 3)
- ✅ Hidden input `edit-line-id` (Task 2 Step 4)
- ✅ 5 field baru di modal (Jenis Bayar, Semester, Tahun Ajaran, IPK, Jumlah) (Task 2 Step 5)
- ✅ `openEditById` load line data + populate fields (Task 3 Step 1)
- ✅ `saveEdit` include line fields di payload (Task 3 Step 2)
- ✅ `update_pa` update `lines_tbl` jika `line_id` ada (Task 1 Step 4)
- ✅ Tests: active filter (3 cases) + line update (Task 1 Step 1)

**Placeholder scan:** Tidak ada TBD/TODO.

**Type consistency:** `line_id` konsisten sebagai `int` di service test, Python `data.get("line_id")`, dan JS `parseInt(...)`. `ipk_sem_sebelumnya` dan `jumlah_pembayaran` sebagai `float`/`REAL` konsisten di semua layer.
