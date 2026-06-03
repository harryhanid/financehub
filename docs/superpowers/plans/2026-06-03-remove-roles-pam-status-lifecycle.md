# Remove Role System + PAM/PA Status Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hapus role-based access control dari seluruh sistem, dan implementasi PAM status lifecycle baru (draft → on_process → complete) dengan cascade tanggal_bayar ke etf_pa.

**Architecture:** Tiga perubahan independen dijalankan berurutan: (1) DB migration tambah kolom, (2) ganti semua role middleware ke jwt_html_required di Python, (3) update payment_memo status logic + cascade, (4) bersihkan template dari role checks.

**Tech Stack:** Python/Flask, SQLite, Jinja2, Vanilla JS

---

## File Map

| File | Perubahan |
|---|---|
| `app/database.py` | Migration: tambah `payment_memo.tanggal_bayar` |
| `app/modules/payment_memo/service.py` | Update status values, tambah cascade ke etf_pa |
| `app/modules/payment_memo/routes.py` | Ganti semua role_required → jwt_html_required, tambah endpoint tanggal_bayar |
| `app/modules/payment_memo/api.py` | Ganti api_role_required → jwt_html_required |
| `app/modules/beasiswa/routes.py` | Ganti semua role_required → jwt_html_required |
| `app/modules/beasiswa/api.py` | Ganti api_role_required → jwt_html_required |
| `app/modules/etf_payment_application/routes.py` | Ganti role_required → jwt_html_required |
| `app/modules/payment_application/routes.py` | Ganti role_required → jwt_html_required |
| `app/modules/users/routes.py` | Ganti html_role_required/role_required → jwt_html_required |
| `app/templates/base.html` | Hapus kondisi `current_role == 'releaser'` di sidebar |
| `app/templates/beasiswa/index.html` | Hapus semua `{% if current_role %}` checks |
| `app/templates/payment_memo/index.html` | Hapus role checks, update status UI, tambah tombol Submit + field tanggal_bayar |
| `app/templates/payment_application/index.html` | Hapus role checks |
| `app/templates/dashboard/index.html` | Hapus role check di User Management link |

---

## Task 1: DB Migration — Tambah tanggal_bayar ke payment_memo

**Files:**
- Modify: `app/database.py`

- [ ] **Step 1: Tambah kolom ke DDL payment_memo**

Di `app/database.py`, cari `CREATE TABLE IF NOT EXISTS payment_memo`. Pastikan ada kolom `tanggal_bayar TEXT` setelah kolom `total_amount`. Jika belum ada, tambahkan:

```sql
CREATE TABLE IF NOT EXISTS payment_memo (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER NOT NULL REFERENCES companies(id),
    memo_number  TEXT,
    tanggal      TEXT,
    total_amount REAL DEFAULT 0,
    tanggal_bayar TEXT,
    status       TEXT DEFAULT 'draft',
    notes        TEXT,
    created_by   TEXT,
    approved_by  TEXT,
    approved_at  TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at   TEXT
);
```

- [ ] **Step 2: Tambah migration idempoten di migrate_db()**

Di fungsi `migrate_db()`, dalam blok try/except yang ada, tambahkan:

```python
try:
    conn.execute("ALTER TABLE payment_memo ADD COLUMN tanggal_bayar TEXT")
except Exception:
    pass
```

- [ ] **Step 3: Verifikasi**

```bash
cd /c/Financehub/app && python -c "
from database import get_conn
conn = get_conn()
cols = [r[1] for r in conn.execute('PRAGMA table_info(payment_memo)').fetchall()]
print(cols)
assert 'tanggal_bayar' in cols
print('OK')
"
```

Expected: list kolom termasuk `tanggal_bayar`, lalu `OK`.

- [ ] **Step 4: Commit**

```bash
git add app/database.py
git commit -m "feat(db): add tanggal_bayar to payment_memo"
```

---

## Task 2: Update payment_memo Service — Status Lifecycle + Cascade

**Files:**
- Modify: `app/modules/payment_memo/service.py`

- [ ] **Step 1: Update `update_memo_status` — status values baru**

Di `app/modules/payment_memo/service.py`, cari fungsi `update_memo_status`. Ganti seluruh fungsi dengan versi baru yang menggunakan status `draft/on_process/complete` dan hapus logic approved_by/approved_at yang tidak diperlukan lagi:

```python
def update_memo_status(memo_id: int, new_status: str, by_user: str, company_id: int = 0) -> dict:
    allowed = {"draft", "on_process", "complete"}
    if new_status not in allowed:
        return {"ok": False, "pesan": f"Status '{new_status}' tidak valid."}

    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM payment_memo WHERE id=? AND (? = 0 OR company_id=?)",
        (memo_id, company_id, company_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Memo tidak ditemukan."}

    now = _ts()
    conn.execute(
        "UPDATE payment_memo SET status=?, updated_at=? WHERE id=?",
        (new_status, now, memo_id)
    )

    if new_status == "complete":
        # Update payment_beasiswa rows linked to this memo
        conn.execute(
            "UPDATE payment_beasiswa SET status='paid' WHERE memo_id=?",
            (memo_id,)
        )

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"Status memo diubah ke '{new_status}'."}
```

- [ ] **Step 2: Tambah fungsi `set_memo_tanggal_bayar` dengan cascade ke etf_pa**

Setelah fungsi `update_memo_status`, tambahkan fungsi baru:

```python
def set_memo_tanggal_bayar(memo_id: int, tanggal_bayar: str, company_id: int) -> dict:
    """
    Set tanggal_bayar di payment_memo → status complete,
    cascade ke etf_pa: tanggal_bayar + status=complete.
    """
    if not tanggal_bayar:
        return {"ok": False, "pesan": "Tanggal bayar wajib diisi."}

    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM payment_memo WHERE id=? AND company_id=?",
        (memo_id, company_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Memo tidak ditemukan."}

    now = _ts()

    # 1. Update payment_memo
    conn.execute(
        "UPDATE payment_memo SET tanggal_bayar=?, status='complete', updated_at=? WHERE id=?",
        (tanggal_bayar, now, memo_id)
    )

    # 2. Update payment_beasiswa status
    conn.execute(
        "UPDATE payment_beasiswa SET status='paid' WHERE memo_id=?",
        (memo_id,)
    )

    # 3. Cascade ke etf_pa: ambil semua etf_pa_line_id dari payment_beasiswa rows di memo ini
    lines = conn.execute(
        "SELECT DISTINCT etf_pa_line_id FROM payment_beasiswa WHERE memo_id=? AND etf_pa_line_id IS NOT NULL",
        (memo_id,)
    ).fetchall()
    line_ids = [r[0] for r in lines]

    if line_ids:
        ph = ",".join("?" * len(line_ids))
        conn.execute(
            f"""UPDATE etf_pa SET tanggal_bayar=?, status='complete', updated_at=?
                WHERE id IN (
                    SELECT DISTINCT pa_id FROM etf_pa_lines WHERE id IN ({ph})
                ) AND company_id=?""",
            [tanggal_bayar, now] + line_ids + [company_id]
        )

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Tanggal bayar berhasil disimpan."}
```

- [ ] **Step 3: Verifikasi fungsi bisa diimport**

```bash
cd /c/Financehub/app && python -c "
from modules.payment_memo.service import update_memo_status, set_memo_tanggal_bayar
print('Import OK')
"
```

Expected: `Import OK`

- [ ] **Step 4: Commit**

```bash
git add app/modules/payment_memo/service.py
git commit -m "feat(payment-memo): new status lifecycle draft/on_process/complete + cascade tanggal_bayar ke etf_pa"
```

---

## Task 3: Update payment_memo Routes — Hapus Role + Endpoint Baru

**Files:**
- Modify: `app/modules/payment_memo/routes.py`
- Modify: `app/modules/payment_memo/api.py`

- [ ] **Step 1: Ganti semua role_required di payment_memo/routes.py**

Di `app/modules/payment_memo/routes.py`:

1. Ganti import:
```python
# Hapus ini:
from auth.middleware import jwt_html_required, role_required
# Ganti dengan:
from auth.middleware import jwt_html_required
```

2. Ganti semua `@role_required(...)` dengan `@jwt_html_required` menggunakan search-replace. Setiap pola seperti:
```python
@role_required("requester", "verificator", "releaser")
```
atau
```python
@role_required("verificator")
```
atau
```python
@role_required("verificator", "releaser")
```
→ semua ganti jadi:
```python
@jwt_html_required
```

- [ ] **Step 2: Tambah import set_memo_tanggal_bayar ke routes.py**

Di bagian import service di `payment_memo/routes.py`, tambahkan `set_memo_tanggal_bayar`:

```python
from modules.payment_memo.service import (
    # ... fungsi yang sudah ada ...,
    set_memo_tanggal_bayar,
)
```

- [ ] **Step 3: Tambah endpoint POST /payment-memo/<id>/tanggal-bayar**

Di akhir `payment_memo/routes.py`, sebelum baris terakhir, tambahkan:

```python
@bp.route("/<int:memo_id>/tanggal-bayar", methods=["POST"])
@jwt_html_required
def memo_tanggal_bayar(memo_id):
    company_id = session.get("company_id")
    data = request.get_json(force=True) or {}
    return jsonify(set_memo_tanggal_bayar(
        memo_id,
        data.get("tanggal_bayar", ""),
        company_id,
    ))
```

- [ ] **Step 4: Ganti api_role_required di payment_memo/api.py**

Di `app/modules/payment_memo/api.py`:

```python
# Ganti:
from auth.middleware import api_role_required
# Dengan:
from auth.middleware import jwt_html_required
```

Ganti semua `@api_role_required(...)` dengan `@jwt_html_required`.

- [ ] **Step 5: Verifikasi import**

```bash
cd /c/Financehub/app && python -c "
from modules.payment_memo.routes import bp
from modules.payment_memo.api import bp as api_bp
print('Routes import OK')
"
```

Expected: `Routes import OK`

- [ ] **Step 6: Commit**

```bash
git add app/modules/payment_memo/routes.py app/modules/payment_memo/api.py
git commit -m "refactor(payment-memo): remove role_required, add tanggal-bayar endpoint"
```

---

## Task 4: Hapus Role di Semua Module Routes Lainnya

**Files:**
- Modify: `app/modules/beasiswa/routes.py`
- Modify: `app/modules/beasiswa/api.py`
- Modify: `app/modules/etf_payment_application/routes.py`
- Modify: `app/modules/payment_application/routes.py`
- Modify: `app/modules/users/routes.py`

- [ ] **Step 1: Update beasiswa/routes.py**

```python
# Ganti import:
from auth.middleware import jwt_html_required, role_required
# Dengan:
from auth.middleware import jwt_html_required
```

Ganti semua `@role_required(...)` → `@jwt_html_required` di seluruh file.

- [ ] **Step 2: Update beasiswa/api.py**

```python
# Ganti:
from auth.middleware import api_role_required
# Dengan:
from auth.middleware import jwt_html_required
```

Ganti semua `@api_role_required(...)` → `@jwt_html_required`.

- [ ] **Step 3: Update etf_payment_application/routes.py**

File ini sudah sebagian menggunakan `role_required` (dari Task 3 kemarin — draft-siswa dan draft-lines). Ganti sisa yang masih `role_required`:

```python
# Ganti import:
from auth.middleware import jwt_html_required, role_required
# Dengan:
from auth.middleware import jwt_html_required
```

Ganti semua `@role_required(...)` → `@jwt_html_required`.

- [ ] **Step 4: Update payment_application/routes.py**

```python
from auth.middleware import jwt_html_required
```

Ganti semua `@role_required(...)` → `@jwt_html_required`.

- [ ] **Step 5: Update users/routes.py**

```python
from auth.middleware import jwt_html_required
```

Ganti `@html_role_required("releaser")` → `@jwt_html_required`
Ganti `@role_required("releaser")` → `@jwt_html_required`

- [ ] **Step 6: Verifikasi semua imports bersih**

```bash
cd /c/Financehub/app && python -c "
import app
print('App imports OK')
" 2>&1 | head -20
```

Jika error, perbaiki import yang bermasalah.

- [ ] **Step 7: Commit**

```bash
git add app/modules/beasiswa/routes.py app/modules/beasiswa/api.py \
        app/modules/etf_payment_application/routes.py \
        app/modules/payment_application/routes.py \
        app/modules/users/routes.py
git commit -m "refactor: remove role_required from all routes, all users have full access"
```

---

## Task 5: Update Templates — Hapus Role Checks

**Files:**
- Modify: `app/templates/base.html`
- Modify: `app/templates/beasiswa/index.html`
- Modify: `app/templates/payment_memo/index.html`
- Modify: `app/templates/payment_application/index.html`
- Modify: `app/templates/dashboard/index.html`

- [ ] **Step 1: base.html — Hapus kondisi role di sidebar Admin**

Cari di `app/templates/base.html`:
```html
{% if current_role == 'releaser' %}
<div class="sidebar-section">Admin</div>
<a href="/users" {% if active_page == 'users' %}class="active"{% endif %}>
  ...
  User Management
</a>
{% endif %}
```

Ganti dengan (hapus kondisi, selalu tampil):
```html
<div class="sidebar-section">Admin</div>
<a href="/users" {% if active_page == 'users' %}class="active"{% endif %}>
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
  User Management
</a>
```

- [ ] **Step 2: beasiswa/index.html — Hapus semua role checks**

Cari dan perbaiki setiap kondisi berikut di `app/templates/beasiswa/index.html`:

a. `{% if current_role in ['requester','verificator','releaser'] %}` → hapus kondisi, isi selalu tampil

b. `{% if current_role == 'requester' %}` → hapus kondisi, isi selalu tampil

Untuk setiap blok `{% if current_role ... %}...{% endif %}`, pertahankan isi (konten di dalam) tapi hapus kondisi if/endif-nya.

- [ ] **Step 3: dashboard/index.html — Hapus role check**

Cari:
```html
{% if current_role == 'releaser' %}<a href="/users" class="btn btn-secondary">User Management</a>{% endif %}
```

Ganti dengan:
```html
<a href="/users" class="btn btn-secondary">User Management</a>
```

- [ ] **Step 4: payment_application/index.html — Hapus role checks**

Cari semua `{% if current_role == 'releaser' %}` dan hapus kondisi, tampilkan konten selalu.

- [ ] **Step 5: payment_memo/index.html — Refactor status UI + hapus role checks**

Ini file yang paling banyak berubah. Lakukan perubahan berikut:

**a. Hapus semua role-based conditional dari template:**

Ganti setiap `{% if current_role == 'verificator' %}` atau `{% if current_role in ['verificator', 'releaser'] %}` atau `{% if current_role == 'releaser' %}`:
- Jika kontennya adalah kolom/tombol aksi → pertahankan konten, hapus kondisi
- Jika kontennya adalah `colspan` dinamis → ganti dengan angka tetap

**b. Update status badge labels:**

Cari semua badge status di template, pastikan menampilkan label yang benar:
```html
<span class="badge {% if m.status == 'complete' %}badge-green{% elif m.status == 'on_process' %}badge-yellow{% else %}badge-gray{% endif %}">
  {{ m.status | replace('_', ' ') | title }}
</span>
```

**c. Ganti CURRENT_ROLE JavaScript variable:**

Cari:
```javascript
const CURRENT_ROLE = {{ current_role | tojson }};
```

Hapus baris ini dan ganti semua referensi `CURRENT_ROLE` dalam JavaScript dengan logic yang tidak bergantung role. Biasanya kondisinya adalah "tampilkan tombol aksi" — ganti jadi selalu tampil.

**d. Tambah tombol Submit (draft → on_process) dan field tanggal_bayar:**

Di bagian detail/modal PAM, tambahkan:
```html
<!-- Tombol Submit PAM -->
<button class="btn btn-primary btn-sm" onclick="submitMemo(memoId)"
  id="btn-submit-memo" style="display:none">
  Submit / Proses
</button>

<!-- Field tanggal bayar -->
<div class="form-group" id="tgl-bayar-section" style="display:none">
  <label>Tanggal Bayar</label>
  <input type="date" id="input-tgl-bayar">
  <button class="btn btn-success btn-sm" onclick="saveTanggalBayar(memoId)">
    Simpan Tanggal Bayar
  </button>
</div>
```

Tombol Submit muncul jika `status == 'draft'`, field tanggal bayar muncul jika `status == 'on_process'`.

**e. Tambah JavaScript functions untuk Submit dan Tanggal Bayar:**

```javascript
async function submitMemo(memoId) {
  if (!memoId) return;
  const d = await (await apiFetch(`/payment-memo/${memoId}/update-status`, {
    method: "POST",
    body: JSON.stringify({ status: "on_process" })
  })).json();
  showToast(d.pesan, d.ok ? "success" : "error");
  if (d.ok) loadMemoList();
}

async function saveTanggalBayar(memoId) {
  const tgl = document.getElementById("input-tgl-bayar").value;
  if (!tgl) { showToast("Pilih tanggal bayar dulu.", "error"); return; }
  const d = await (await apiFetch(`/payment-memo/${memoId}/tanggal-bayar`, {
    method: "POST",
    body: JSON.stringify({ tanggal_bayar: tgl })
  })).json();
  showToast(d.pesan, d.ok ? "success" : "error");
  if (d.ok) loadMemoList();
}
```

- [ ] **Step 6: Commit**

```bash
git add app/templates/
git commit -m "refactor(templates): remove role checks, update payment_memo status UI"
```

---

## Task 6: Verifikasi End-to-End

- [ ] **Step 1: Run tests**

```bash
cd /c/Financehub && python -m pytest app/tests/ -v 2>&1 | tail -10
```

Expected: semua test pass (atau hanya test yang memang cek role yang fail — update test tersebut).

- [ ] **Step 2: Test flow manual**

1. Login sebagai user manapun
2. Pastikan sidebar menampilkan User Management (sebelumnya hanya releaser)
3. Buat PA baru di ETF PA → status draft
4. Input Payment → cari siswa → pilih kategori → submit → PA berubah on_process, PAM terbuat draft
5. Buka PAM Records → klik Submit → PAM berubah on_process
6. Isi tanggal bayar di PAM → PAM complete, PA complete, tanggal_bayar terisi di PA

- [ ] **Step 3: Final commit jika ada fix**

```bash
git add -p
git commit -m "fix: address e2e verification findings"
git push origin master
```
