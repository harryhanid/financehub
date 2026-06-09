# Editable No. PAM di Input PA — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ubah field No. PAM di panel Input PA dari `readonly` menjadi editable, dengan format validation real-time, collision check saat blur, dan guard di save.

**Architecture:** (1) Service function baru `check_pam_no_exists` + route `GET /payment-memo/pam/check`; (2) HTML field: hilangkan `readonly`, tambah hint div; (3) JS: regex validator + async collision checker + updated save guard. Tipe/tanggal change tetap auto-overwrite (behaviour yang ada).

**Tech Stack:** Flask (Python), SQLite, vanilla JS inline di Jinja2 template.

---

## File Map

| File | Perubahan |
|------|-----------|
| `app/modules/payment_memo/service.py` | Tambah `check_pam_no_exists()` di akhir file |
| `app/modules/payment_memo/routes.py` | Import `check_pam_no_exists`; tambah route `GET /pam/check` |
| `app/templates/payment_memo/index.html` | (1) HTML: ubah field No. PAM; (2) JS: `_PAM_RE`, `_ipayResetPamState`, `ipayValidatePamNo`, `ipayCheckPamCollision`, update `ipayFetchNextPamNo`, update `ipaySavePa` |
| `tests/test_payment_memo_ipay.py` | Tambah test `check_pam_no_exists` |

---

## Task 1 — Service: `check_pam_no_exists`

**Files:**
- Modify: `app/modules/payment_memo/service.py` (append at end)
- Test: `tests/test_payment_memo_ipay.py`

- [ ] **Step 1: Tulis failing test**

Tambahkan ke `tests/test_payment_memo_ipay.py`:

```python
import sqlite3, tempfile, os

def _make_db(path):
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE pam_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            pam_no TEXT NOT NULL,
            pam_date TEXT,
            requestors_name TEXT,
            keterangan TEXT,
            total_amount REAL DEFAULT 0,
            due_date TEXT,
            source TEXT,
            status TEXT DEFAULT 'draft',
            created_at TEXT
        )
    """)
    conn.execute(
        "INSERT INTO pam_records (company_id, pam_no, source) VALUES (1, 'PAM-001-AGRI-06-2026', 'agri')"
    )
    conn.commit()
    conn.close()
    return path


def test_check_pam_no_exists_true(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    _make_db(db_path)
    import app.database as db_mod
    def _fake_conn():
        import sqlite3 as _sq
        c = _sq.connect(db_path)
        c.row_factory = _sq.Row
        return c
    monkeypatch.setattr(db_mod, "get_conn", _fake_conn)
    from app.modules.payment_memo.service import check_pam_no_exists
    result = check_pam_no_exists(1, "PAM-001-AGRI-06-2026")
    assert result == {"ok": True, "exists": True}


def test_check_pam_no_exists_false(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    _make_db(db_path)
    import app.database as db_mod
    def _fake_conn():
        import sqlite3 as _sq
        c = _sq.connect(db_path)
        c.row_factory = _sq.Row
        return c
    monkeypatch.setattr(db_mod, "get_conn", _fake_conn)
    from app.modules.payment_memo.service import check_pam_no_exists
    result = check_pam_no_exists(1, "PAM-099-AGRI-06-2026")
    assert result == {"ok": True, "exists": False}


def test_check_pam_no_wrong_company(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    _make_db(db_path)
    import app.database as db_mod
    def _fake_conn():
        import sqlite3 as _sq
        c = _sq.connect(db_path)
        c.row_factory = _sq.Row
        return c
    monkeypatch.setattr(db_mod, "get_conn", _fake_conn)
    from app.modules.payment_memo.service import check_pam_no_exists
    # Same pam_no but different company_id — should NOT exist
    result = check_pam_no_exists(99, "PAM-001-AGRI-06-2026")
    assert result == {"ok": True, "exists": False}
```

- [ ] **Step 2: Jalankan test untuk verifikasi FAIL**

```
cd C:\Financehub
python -m pytest tests/test_payment_memo_ipay.py::test_check_pam_no_exists_true -v
```

Expected: `FAILED` dengan `ImportError: cannot import name 'check_pam_no_exists'`

- [ ] **Step 3: Tambahkan fungsi ke service.py**

Append ke bawah `app/modules/payment_memo/service.py`:

```python
def check_pam_no_exists(company_id: int, pam_no: str) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM pam_records WHERE pam_no=? AND company_id=?",
        (pam_no, company_id)
    ).fetchone()
    conn.close()
    return {"ok": True, "exists": row is not None}
```

- [ ] **Step 4: Jalankan semua 3 test baru + existing**

```
cd C:\Financehub
python -m pytest tests/test_payment_memo_ipay.py -v
```

Expected output (semua PASS):
```
tests/test_payment_memo_ipay.py::test_setf_in_valid_tabs PASSED
tests/test_payment_memo_ipay.py::test_setf_tab_config PASSED
tests/test_payment_memo_ipay.py::test_tbls_setf_resolves PASSED
tests/test_payment_memo_ipay.py::test_check_pam_no_exists_true PASSED
tests/test_payment_memo_ipay.py::test_check_pam_no_exists_false PASSED
tests/test_payment_memo_ipay.py::test_check_pam_no_wrong_company PASSED
```

- [ ] **Step 5: Commit**

```bash
git add app/modules/payment_memo/service.py tests/test_payment_memo_ipay.py
git commit -m "feat: add check_pam_no_exists service function"
```

---

## Task 2 — Route: `GET /payment-memo/pam/check`

**Files:**
- Modify: `app/modules/payment_memo/routes.py`

- [ ] **Step 1: Update import di routes.py**

Di `app/modules/payment_memo/routes.py`, baris 5–23, tambahkan `check_pam_no_exists` ke import dari service:

Cari baris:
```python
    get_next_pam_no, save_pa_payment,
```

Ganti dengan:
```python
    get_next_pam_no, save_pa_payment, check_pam_no_exists,
```

- [ ] **Step 2: Tambah route baru sebelum `/ipay/next-pam-no`**

Di `app/modules/payment_memo/routes.py`, cari blok:
```python
@bp.route("/ipay/next-pam-no")
@jwt_html_required
def ipay_next_pam_no():
```

Sisipkan sebelumnya:
```python
@bp.route("/pam/check")
@jwt_html_required
def check_pam_no_route():
    pam_no = (request.args.get("pam_no") or "").strip()
    if not pam_no:
        return jsonify({"ok": True, "exists": False})
    return jsonify(check_pam_no_exists(session.get("company_id", 0), pam_no))


```

- [ ] **Step 3: Smoke-test route tersambung**

```
cd C:\Financehub
python -c "from app.modules.payment_memo.routes import bp; rules = [str(r) for r in bp.url_map.rules if 'check' in str(r).lower() or True]; print([str(r) for r in bp.deferred_functions])"
```

Atau cukup jalankan test suite untuk pastikan tidak ada import error:

```
python -m pytest tests/test_payment_memo_ipay.py -v
```

Expected: semua 6 test PASS, tidak ada error.

- [ ] **Step 4: Commit**

```bash
git add app/modules/payment_memo/routes.py
git commit -m "feat: add GET /pam/check route for PAM number collision detection"
```

---

## Task 3 — HTML: Ubah Field No. PAM

**Files:**
- Modify: `app/templates/payment_memo/index.html` (HTML section ~baris 107–111)

- [ ] **Step 1: Ganti blok form-group No. PAM**

Cari (baris 107–111):
```html
      <div class="form-group" style="margin:0">
        <label>No. PAM <span id="ipay-pam-type-badge" style="font-size:.65rem;color:#10b981;font-weight:400">(auto AGRI)</span></label>
        <input type="text" id="ipay-pam-full" readonly placeholder="Memuat..."
               style="font-family:monospace;font-weight:700;color:#1d4ed8;background:#f0f9ff;cursor:default">
      </div>
```

Ganti dengan:
```html
      <div class="form-group" style="margin:0">
        <label>No. PAM
          <span id="ipay-pam-type-badge" style="font-size:.65rem;color:#10b981;font-weight:400">(auto AGRI)</span>
          <span id="ipay-pam-manual-badge" style="display:none;font-size:.65rem;color:#f59e0b;font-weight:600;margin-left:.25rem">(manual)</span>
        </label>
        <input type="text" id="ipay-pam-full" placeholder="Memuat..."
               style="font-family:monospace;font-weight:700;color:#1d4ed8;border:1.5px solid #93c5fd;background:#f0f9ff"
               oninput="ipayValidatePamNo()"
               onblur="ipayCheckPamCollision()">
        <div id="ipay-pam-hint" style="display:none;font-size:.68rem;color:#dc2626;margin-top:.2rem"></div>
      </div>
```

- [ ] **Step 2: Verifikasi visual di browser**

Jalankan app (`python app/app.py` atau sesuai cara yang biasa), buka Payment Memo → tab Input, pastikan:
- Field No. PAM bisa diklik dan diketik
- Badge "(manual)" tidak terlihat saat pertama buka
- Hint div tidak terlihat

- [ ] **Step 3: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: make No. PAM field editable in Input PA panel"
```

---

## Task 4 — JS: Validation, Collision Check, Save Guard

**Files:**
- Modify: `app/templates/payment_memo/index.html` (JS section ~baris 2320–2342 dan 2671–2708)

### Step 1: Tambah konstanta `_PAM_RE` dan fungsi helper

- [ ] **Step 1: Cari blok `ipayOnTypeChange` (sekitar baris 2320)**

Cari baris:
```javascript
function ipayOnTypeChange() {
```

Sisipkan **sebelum** baris tersebut:
```javascript
const _PAM_RE = /^PAM-\d{3}-(AGRI|APP|SML|SETF)-\d{2}-\d{4}$/;

function _ipayResetPamState() {
  const pamEl = document.getElementById("ipay-pam-full");
  const badge = document.getElementById("ipay-pam-manual-badge");
  const hint  = document.getElementById("ipay-pam-hint");
  const btn   = document.getElementById("ipay-save-btn");
  if (pamEl)  pamEl.style.borderColor = "#93c5fd";
  if (badge)  badge.style.display = "none";
  if (hint)  { hint.style.display = "none"; hint.textContent = ""; }
  if (btn)    btn.disabled = false;
}

function ipayValidatePamNo() {
  const pamEl = document.getElementById("ipay-pam-full");
  const badge = document.getElementById("ipay-pam-manual-badge");
  const hint  = document.getElementById("ipay-pam-hint");
  const btn   = document.getElementById("ipay-save-btn");
  if (!pamEl) return;
  const val = pamEl.value.trim();
  if (badge) badge.style.display = "inline";
  if (_PAM_RE.test(val)) {
    pamEl.style.borderColor = "#f59e0b";
    if (hint) { hint.style.display = "none"; hint.textContent = ""; }
    if (btn) btn.disabled = false;
  } else {
    pamEl.style.borderColor = "#dc2626";
    if (hint) { hint.style.display = "block"; hint.textContent = "Format: PAM-054-AGRI-06-2026"; }
    if (btn) btn.disabled = true;
  }
}

async function ipayCheckPamCollision() {
  const pamEl = document.getElementById("ipay-pam-full");
  const badge = document.getElementById("ipay-pam-manual-badge");
  if (!pamEl || !badge || badge.style.display === "none") return;
  const val = pamEl.value.trim();
  if (!_PAM_RE.test(val)) return;
  try {
    const res = await apiFetch(`/payment-memo/pam/check?pam_no=${encodeURIComponent(val)}`);
    if (!res) return;
    const data = await res.json();
    const hint = document.getElementById("ipay-pam-hint");
    const btn  = document.getElementById("ipay-save-btn");
    if (data.exists) {
      pamEl.style.borderColor = "#dc2626";
      if (hint) { hint.style.display = "block"; hint.textContent = "PAM ini sudah terdaftar"; }
      if (btn) btn.disabled = true;
    } else {
      pamEl.style.borderColor = "#22c55e";
      if (hint) { hint.style.display = "none"; hint.textContent = ""; }
      if (btn) btn.disabled = false;
    }
  } catch { /* ignore network error */ }
}

```

### Step 2: Update `ipayFetchNextPamNo` untuk reset manual state

- [ ] **Step 2: Ganti fungsi `ipayFetchNextPamNo`**

Cari:
```javascript
async function ipayFetchNextPamNo() {
  const type = document.getElementById("ipay-type")?.value || "agri";
  const tgl  = document.getElementById("ipay-tgl")?.value || new Date().toISOString().slice(0, 10);
  const pamEl = document.getElementById("ipay-pam-full");
  if (!pamEl) return;
  pamEl.value = "Memuat...";
  try {
    const res = await apiFetch(`/payment-memo/ipay/next-pam-no?tab=${encodeURIComponent(type)}&date=${encodeURIComponent(tgl)}`);
    if (!res) { pamEl.value = ""; return; }
    const data = await res.json();
    pamEl.value = data.ok ? (data.pam_no || "") : "";
  } catch { pamEl.value = ""; }
}
```

Ganti dengan:
```javascript
async function ipayFetchNextPamNo() {
  const type = document.getElementById("ipay-type")?.value || "agri";
  const tgl  = document.getElementById("ipay-tgl")?.value || new Date().toISOString().slice(0, 10);
  const pamEl = document.getElementById("ipay-pam-full");
  if (!pamEl) return;
  pamEl.value = "Memuat...";
  try {
    const res = await apiFetch(`/payment-memo/ipay/next-pam-no?tab=${encodeURIComponent(type)}&date=${encodeURIComponent(tgl)}`);
    if (!res) { pamEl.value = ""; return; }
    const data = await res.json();
    pamEl.value = data.ok ? (data.pam_no || "") : "";
  } catch { pamEl.value = ""; }
  _ipayResetPamState();
}
```

### Step 3: Update `ipaySavePa` — tambah format + collision guard

- [ ] **Step 3: Ganti fungsi `ipaySavePa`**

Cari:
```javascript
async function ipaySavePa() {
  const type       = document.getElementById("ipay-type")?.value || "agri";
  const tanggal    = document.getElementById("ipay-tgl").value;
  const pam_no     = document.getElementById("ipay-pam-full").value.trim();
  const keterangan = document.getElementById("ipay-catatan")?.value.trim() || "";
  const pillar     = document.getElementById("ipay-pillar").value;
  const perusahaan = document.getElementById("ipay-perusahaan").value;

  if (!tanggal || !pam_no || pam_no === "Memuat...") {
    showToast("Tanggal dan No. PAM wajib ada.", "error"); return;
  }
  if (!perusahaan) { showToast("Perusahaan wajib diisi.", "error"); return; }
```

Ganti dengan:
```javascript
async function ipaySavePa() {
  const type       = document.getElementById("ipay-type")?.value || "agri";
  const tanggal    = document.getElementById("ipay-tgl").value;
  const pam_no     = document.getElementById("ipay-pam-full").value.trim();
  const keterangan = document.getElementById("ipay-catatan")?.value.trim() || "";
  const pillar     = document.getElementById("ipay-pillar").value;
  const perusahaan = document.getElementById("ipay-perusahaan").value;

  if (!tanggal || !pam_no || pam_no === "Memuat...") {
    showToast("Tanggal dan No. PAM wajib ada.", "error"); return;
  }
  if (!_PAM_RE.test(pam_no)) {
    showToast("No. PAM tidak valid. Format: PAM-054-AGRI-06-2026", "error"); return;
  }
  const badge = document.getElementById("ipay-pam-manual-badge");
  if (badge && badge.style.display !== "none") {
    const chkRes = await apiFetch(`/payment-memo/pam/check?pam_no=${encodeURIComponent(pam_no)}`);
    if (chkRes) {
      const chk = await chkRes.json();
      if (chk.exists) {
        const hint  = document.getElementById("ipay-pam-hint");
        const pamEl = document.getElementById("ipay-pam-full");
        const btn   = document.getElementById("ipay-save-btn");
        if (pamEl) pamEl.style.borderColor = "#dc2626";
        if (hint)  { hint.style.display = "block"; hint.textContent = "PAM ini sudah terdaftar"; }
        if (btn)   btn.disabled = true;
        showToast("No. PAM sudah terdaftar.", "error"); return;
      }
    }
  }
  if (!perusahaan) { showToast("Perusahaan wajib diisi.", "error"); return; }
```

- [ ] **Step 4: Jalankan test suite untuk pastikan tidak ada regresi**

```
cd C:\Financehub
python -m pytest tests/test_payment_memo_ipay.py -v
```

Expected: semua 6 test PASS.

- [ ] **Step 5: Verifikasi end-to-end di browser**

1. Buka Payment Memo → tab Input
2. Pilih Tipe + isi Tanggal → field No. PAM auto-fill, badge "(manual)" tidak muncul
3. Ketik karakter bebas di field No. PAM → badge "(manual)" muncul, border merah, hint "Format: PAM-054-AGRI-06-2026"
4. Ketik format valid misal `PAM-099-AGRI-06-2026` → border oranye, hint hilang
5. Klik keluar dari field (blur) → jika nomor belum ada di DB, border hijau; jika sudah ada, border merah + hint "PAM ini sudah terdaftar"
6. Ubah Tipe → field auto-overwrite, badge "(manual)" hilang, border kembali biru muda
7. Coba klik Simpan dengan nomor manual collision → toast "No. PAM sudah terdaftar."

- [ ] **Step 6: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add PAM number validation and collision check in Input PA"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Field editable (Task 3)
- ✅ Badge "(manual)" muncul saat edit (Task 4 Step 1 `ipayValidatePamNo`)
- ✅ Style auto: biru muda; manual valid: oranye; error: merah (Tasks 3–4)
- ✅ Tipe/tanggal change → auto-overwrite + reset state (Task 4 Step 2)
- ✅ Format regex `PAM-\d{3}-(AGRI|APP|SML|SETF)-\d{2}-\d{4}` (Task 4 Step 1)
- ✅ Collision check saat blur (Task 4 Step 1 `ipayCheckPamCollision`)
- ✅ Save guard: format check + collision re-check saat manual mode (Task 4 Step 3)
- ✅ Backend endpoint `GET /pam/check` (Task 2)
- ✅ Service `check_pam_no_exists` dengan company isolation (Task 1)
- ✅ Tests untuk semua 3 kasus: exists, not-exists, wrong-company (Task 1)

**Placeholder scan:** Tidak ada TBD/TODO.

**Type consistency:** `check_pam_no_exists(company_id: int, pam_no: str) -> dict` dipakai konsisten di service, route, dan test.
