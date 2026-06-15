# PAM Workflow Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix double pam_records bug, LAND prefix, and frontend regex so the Input PAM workflow creates exactly one correct record per submit.

**Architecture:** Extract `insert_payment_rows()` as a shared helper in `beasiswa/service.py` that only inserts rows and returns IDs+total (no pam_record creation). `add_payment_multi` becomes a thin wrapper (old flow unchanged). `save_pa_payment` calls the new helper instead, so it controls pam_record creation with the user's chosen pam_no and correct total.

**Tech Stack:** Python/Flask, SQLite, Jinja2 HTML templates, vanilla JS

---

## File Map

| File | Change |
|---|---|
| `app/modules/beasiswa/service.py` | Add `insert_payment_rows()`, refactor `add_payment_multi` as wrapper |
| `app/modules/payment_memo/service.py` | Fix `_IPAY_PAM_PREFIX["sml"]`, fix `save_pa_payment` |
| `app/templates/payment_memo/index.html` | Fix regex, ipayOnTypeChange, btn guard, hint msg |
| `app/tests/test_pam_service.py` | Add 3 new test functions |

---

## Task 1: Add `insert_payment_rows()` helper + refactor `add_payment_multi`

**Files:**
- Modify: `app/modules/beasiswa/service.py`
- Test: `app/tests/test_pam_service.py`

- [ ] **Step 1: Write failing test for `insert_payment_rows`**

Add to `app/tests/test_pam_service.py`:

```python
# add to imports at top of file:
# from modules.beasiswa.service import insert_payment_rows

def test_insert_payment_rows_returns_ids_and_total():
    from modules.beasiswa.service import insert_payment_rows
    conn = get_conn()
    rows = [
        {"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
         "amount": 5_000_000},
        {"siswa_code": "S002", "cat1": "By Pendidikan", "cat2": "Semester 2",
         "amount": 3_000_000},
    ]
    result = insert_payment_rows(conn, COMPANY_ID, COMPANY_CODE,
                                  "2026-06-15", "ETF", "PT. ABC", rows)
    conn.commit()
    # Verify return shape
    assert result["ok"] is True
    assert len(result["payment_ids"]) == 2
    assert result["total"] == 8_000_000
    # Verify NO pam_records created
    count = conn.execute("SELECT COUNT(*) FROM pam_records").fetchone()[0]
    conn.close()
    assert count == 0
```

- [ ] **Step 2: Run test to verify it fails**

```
cd app && python -m pytest tests/test_pam_service.py::test_insert_payment_rows_returns_ids_and_total -v
```

Expected: `FAILED` — `ImportError: cannot import name 'insert_payment_rows'`

- [ ] **Step 3: Add `insert_payment_rows()` to `app/modules/beasiswa/service.py`**

Insert this function **before** `add_payment_multi` (before line 327):

```python
def insert_payment_rows(conn, company_id: int, company_code: str,
                        tanggal: str, pillar: str, perusahaan: str,
                        rows: list) -> dict:
    """Insert payment_beasiswa rows and update linked PA status → on_process.

    Caller owns conn (no commit, no close here). Does NOT create pam_record.
    Returns {"ok": bool, "payment_ids": list, "total": float, "pa_line_ids": list}.
    """
    saved = 0
    payment_ids: list = []
    total = 0.0

    for row in rows:
        try:
            amount = float(str(row.get("amount", 0)).replace(",", ""))
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0:
            continue

        if row.get("cat1") == "By Medical" and row.get("cat2") in _CAT2_MEDICAL:
            rm = row.get("rekam_medis") or {}
            if not rm.get("kelas") or not rm.get("rumah_sakit") or \
               not rm.get("diagnosa") or not rm.get("spesialisasi"):
                return {"ok": False,
                        "pesan": "Data rekam medis wajib diisi (kelas, rumah sakit, diagnosa, spesialisasi).",
                        "payment_ids": [], "total": 0.0, "pa_line_ids": []}

        siswa_code     = (row.get("siswa_code") or "").strip()
        etf_pa_line_id = row.get("etf_pa_line_id") or None
        cur = conn.execute(
            """INSERT INTO payment_beasiswa
               (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,
                tgl_pengajuan,tgl_receive,tgl_pa,tgl_final,cat3,cat4,etf_pa_line_id,status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'open')""",
            (company_id, siswa_code,
             row.get("cat1", ""), row.get("cat2", ""),
             tanggal, amount, pillar, perusahaan,
             row.get("tgl_pengajuan", ""), row.get("tgl_receive", ""),
             row.get("tgl_pa", ""),        row.get("tgl_final", ""),
             row.get("cat3", ""),          row.get("cat4", ""),
             etf_pa_line_id)
        )
        payment_ids.append(cur.lastrowid)
        total += amount
        saved += 1

        if row.get("cat1") == "By Medical" and row.get("cat2") in _CAT2_MEDICAL:
            rm = row.get("rekam_medis", {})
            conn.execute(
                """INSERT INTO rekam_medis
                   (company_id, payment_id, siswa_code, kelas, rumah_sakit,
                    diagnosa, spesialisasi, catatan)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (company_id, cur.lastrowid, siswa_code,
                 rm.get("kelas", ""),    rm.get("rumah_sakit", ""),
                 rm.get("diagnosa", ""), rm.get("spesialisasi", ""),
                 rm.get("catatan", "") or None)
            )

    if saved == 0:
        return {"ok": False, "pesan": "Tidak ada item dengan amount > 0.",
                "payment_ids": [], "total": 0.0, "pa_line_ids": []}

    pa_line_ids = [
        row.get("etf_pa_line_id")
        for row in rows
        if row.get("etf_pa_line_id") and
           float(str(row.get("amount", 0)).replace(",", "") or 0) > 0
    ]
    if pa_line_ids:
        ph = ",".join("?" * len(pa_line_ids))
        ts_op = _ts()
        for lines_tbl, pa_tbl in [
            ("etf_pa_lines", "etf_pa"),
            ("app_pa_lines", "app_pa"),
            ("sml_pa_lines", "sml_pa"),
        ]:
            conn.execute(
                f"""UPDATE {pa_tbl} SET status = 'on_process', updated_at = ?
                    WHERE id IN (
                        SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                    ) AND company_id = ? AND status = 'open'""",
                [ts_op] + pa_line_ids + [company_id]
            )

    return {
        "ok":         True,
        "pesan":      f"{saved} payment berhasil disimpan.",
        "payment_ids": payment_ids,
        "total":       total,
        "pa_line_ids": pa_line_ids,
    }
```

- [ ] **Step 4: Refactor `add_payment_multi` as a thin wrapper**

Replace the entire `add_payment_multi` function body (keep the signature, change everything inside):

```python
def add_payment_multi(company_id: int, company_code: str, tanggal: str,
                      pillar: str, perusahaan: str, rows: list) -> dict:
    conn = get_conn()
    try:
        ins = insert_payment_rows(conn, company_id, company_code,
                                  tanggal, pillar, perusahaan, rows)
        if not ins["ok"]:
            return ins

        payment_ids  = ins["payment_ids"]
        total        = ins["total"]
        pa_line_ids  = ins["pa_line_ids"]
        saved        = len(payment_ids)

        # Collect student names for auto keterangan
        unique_codes = list({
            (row.get("siswa_code") or "").strip()
            for row in rows
            if float(str(row.get("amount", 0)).replace(",", "") or 0) > 0
        })
        name_rows = []
        if unique_codes:
            ph = ",".join("?" * len(unique_codes))
            name_rows = conn.execute(
                f"SELECT nama FROM siswa WHERE company_id=? AND code IN ({ph})",
                [company_id] + unique_codes,
            ).fetchall()
        keterangan = ", ".join(r["nama"] for r in name_rows) if name_rows else ""

        pam_no = create_pam_record(conn, company_id, company_code, {
            "pam_date":     tanggal,
            "pt":           perusahaan,
            "keterangan":   keterangan,
            "total_amount": total,
            "payment_ids":  payment_ids,
        })

        if pa_line_ids and pam_no:
            ph = ",".join("?" * len(pa_line_ids))
            ts_pam = _ts()
            for lines_tbl, pa_tbl in [
                ("etf_pa_lines", "etf_pa"),
                ("app_pa_lines", "app_pa"),
                ("sml_pa_lines", "sml_pa"),
            ]:
                conn.execute(
                    f"""UPDATE {pa_tbl} SET nomor_pam = ?, updated_at = ?
                        WHERE id IN (
                            SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                        ) AND company_id = ?""",
                    [pam_no, ts_pam] + pa_line_ids + [company_id]
                )

        conn.commit()
        return {
            "ok":    True,
            "pesan": f"{saved} payment berhasil disimpan (status: open).",
            "saved": saved,
            "pam_no": pam_no,
        }

    except Exception as exc:
        conn.rollback()
        return {"ok": False, "pesan": f"Gagal menyimpan payment: {exc}", "saved": 0}
    finally:
        conn.close()
```

- [ ] **Step 5: Run test to verify it passes**

```
cd app && python -m pytest tests/test_pam_service.py::test_insert_payment_rows_returns_ids_and_total -v
```

Expected: `PASSED`

- [ ] **Step 6: Run full test suite to check no regression**

```
cd app && python -m pytest tests/ -v
```

Expected: All existing tests pass.

- [ ] **Step 7: Commit**

```bash
git add app/modules/beasiswa/service.py app/tests/test_pam_service.py
git commit -m "refactor: extract insert_payment_rows() from add_payment_multi, old flow unchanged"
```

---

## Task 2: Fix `save_pa_payment` + `_IPAY_PAM_PREFIX` in `payment_memo/service.py`

**Files:**
- Modify: `app/modules/payment_memo/service.py`
- Test: `app/tests/test_pam_service.py`

- [ ] **Step 1: Write two failing tests**

Add to `app/tests/test_pam_service.py`:

```python
def test_save_pa_payment_creates_single_pam_record_with_correct_total():
    from modules.payment_memo.service import save_pa_payment
    rows = [
        {"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
         "amount": 5_000_000},
        {"siswa_code": "S002", "cat1": "By Pendidikan", "cat2": "Semester 2",
         "amount": 3_000_000},
    ]
    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab":        "agri",
        "tanggal":    "2026-06-15",
        "pam_no":     "PAM-001-ETF-06-2026",
        "keterangan": "Test PAM",
        "perusahaan": "PT. ABC",
        "pillar":     "ETF",
        "rows":       rows,
    })
    assert result["ok"] is True
    conn = get_conn()
    records = conn.execute(
        "SELECT * FROM pam_records WHERE company_id=?", (COMPANY_ID,)
    ).fetchall()
    conn.close()
    # Exactly 1 pam_record
    assert len(records) == 1
    assert records[0]["pam_no"]        == "PAM-001-ETF-06-2026"
    assert records[0]["total_amount"]  == 8_000_000


def test_get_next_pam_no_land_prefix():
    from modules.payment_memo.service import get_next_pam_no
    pam_no = get_next_pam_no(COMPANY_ID, COMPANY_CODE, "sml", "2026-06-15")
    assert pam_no == "PAM-001-LAND-06-2026"
```

- [ ] **Step 2: Run to verify they fail**

```
cd app && python -m pytest tests/test_pam_service.py::test_save_pa_payment_creates_single_pam_record_with_correct_total tests/test_pam_service.py::test_get_next_pam_no_land_prefix -v
```

Expected: Both `FAILED` — first creates 2 records with total 0, second returns PAM-001-SML-06-2026.

- [ ] **Step 3: Fix `_IPAY_PAM_PREFIX` in `app/modules/payment_memo/service.py`**

Find the dict (around line 238):

```python
_IPAY_PAM_PREFIX = {
    "agri":  "ETF",
    "app":   "APP",
    "sml":   "SML",
    "setf":  "SETF",
}
```

Change to:

```python
_IPAY_PAM_PREFIX = {
    "agri":  "ETF",
    "app":   "APP",
    "sml":   "LAND",
    "setf":  "SETF",
}
```

- [ ] **Step 4: Fix `save_pa_payment` in `app/modules/payment_memo/service.py`**

Replace the entire `save_pa_payment` function body:

```python
def save_pa_payment(company_id: int, company_code: str, data: dict) -> dict:
    """
    Unified save for Input PA (AGRI/APP/SML/SETF):
    1. Insert payment_beasiswa rows via insert_payment_rows (no pam_record)
    2. Link rows to user-provided pam_no
    3. Create exactly one pam_records entry with correct total
    4. Update PA header: nomor_pam + status='on_process'
    """
    from modules.beasiswa.service import insert_payment_rows
    from modules.etf_payment_application.service import _TAB_CFG

    tab        = (data.get("tab") or "agri").lower()
    tanggal    = data.get("tanggal") or _ts()[:10]
    pam_no     = (data.get("pam_no") or "").strip()
    keterangan = data.get("keterangan") or ""
    perusahaan = data.get("perusahaan") or ""
    pillar     = data.get("pillar") or ""
    rows       = data.get("rows") or []

    if not pam_no:
        return {"ok": False, "pesan": "No. PAM wajib diisi."}
    if not rows:
        return {"ok": False, "pesan": "Minimal 1 baris siswa."}

    pa_tbl, lines_tbl, _, _ = _TAB_CFG.get(tab, _TAB_CFG["agri"])

    conn = get_conn()
    try:
        # 1. Insert payment rows — does NOT create pam_record
        ins = insert_payment_rows(conn, company_id, company_code,
                                  tanggal, pillar, perusahaan, rows)
        if not ins.get("ok"):
            conn.close()
            return ins

        payment_ids = ins["payment_ids"]
        total       = ins["total"]

        # 2. Link payment_beasiswa rows to user pam_no
        if payment_ids:
            ph = ",".join("?" * len(payment_ids))
            conn.execute(
                f"UPDATE payment_beasiswa SET pam=? WHERE id IN ({ph})",
                [pam_no] + list(payment_ids)
            )

        # 3. Create exactly one pam_records entry
        due_date = _add_one_month(tanggal)
        conn.execute(
            """INSERT INTO pam_records
               (company_id, pam_no, pam_date, requestors_name, keterangan,
                total_amount, due_date, source, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,'open',?)""",
            (company_id, pam_no, tanggal,
             company_code, keterangan,
             total, due_date, f"etf_{tab}", _ts())
        )

        # 4. Update PA: nomor_pam + status='on_process'
        line_ids = [r.get("etf_pa_line_id") for r in rows
                    if r.get("etf_pa_line_id")]
        if line_ids:
            ph = ",".join("?" * len(line_ids))
            pa_rows = conn.execute(
                f"SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})",
                line_ids
            ).fetchall()
            pa_ids = [row[0] for row in pa_rows]
            if pa_ids:
                ph2 = ",".join("?" * len(pa_ids))
                conn.execute(
                    f"UPDATE {pa_tbl} SET nomor_pam=?, status='on_process'"
                    f" WHERE id IN ({ph2}) AND company_id=?",
                    [pam_no] + list(pa_ids) + [company_id]
                )

        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return {"ok": False, "pesan": f"Gagal menyimpan: {e}"}

    conn.close()
    return {"ok": True, "pesan": f"PAM {pam_no} berhasil dibuat.", "pam_no": pam_no}
```

- [ ] **Step 5: Run the two new tests to verify they pass**

```
cd app && python -m pytest tests/test_pam_service.py::test_save_pa_payment_creates_single_pam_record_with_correct_total tests/test_pam_service.py::test_get_next_pam_no_land_prefix -v
```

Expected: Both `PASSED`

- [ ] **Step 6: Run full test suite**

```
cd app && python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add app/modules/payment_memo/service.py app/tests/test_pam_service.py
git commit -m "fix: save_pa_payment creates 1 pam_record with correct total; LAND prefix for sml tab"
```

---

## Task 3: Frontend fixes in `payment_memo/index.html`

**Files:**
- Modify: `app/templates/payment_memo/index.html`

Four small surgical edits. Find each with its unique surrounding context.

- [ ] **Step 1: Fix `_PAM_RE` regex**

Find (line ~3047):
```javascript
const _PAM_RE = /^PAM-\d{3}-(AGRI|APP|SML|SETF)-\d{2}-\d{4}$/;
```

Replace with:
```javascript
const _PAM_RE = /^PAM-\d{3}-(ETF|APP|LAND|SETF)-\d{2}-\d{4}$/;
```

- [ ] **Step 2: Fix `ipayOnTypeChange()` — remove double fetch**

Find (line ~3104):
```javascript
function ipayOnTypeChange() {
  const type  = document.getElementById("ipay-type")?.value || "agri";
  const lbl   = _IPAY_LABEL[type] || type.toUpperCase();
  const badge = document.getElementById("ipay-pam-type-badge");
  if (badge) badge.textContent = `(auto ${lbl})`;
  const saveBtn = document.getElementById("ipay-save-btn");
  if (saveBtn) saveBtn.textContent = `\u{1F4BE} Simpan PAM ${lbl}`;
  ipayFetchNextPamNo();
  ipayReset();
}
```

Replace with:
```javascript
function ipayOnTypeChange() {
  const type  = document.getElementById("ipay-type")?.value || "agri";
  const lbl   = _IPAY_LABEL[type] || type.toUpperCase();
  const badge = document.getElementById("ipay-pam-type-badge");
  if (badge) badge.textContent = `(auto ${lbl})`;
  const saveBtn = document.getElementById("ipay-save-btn");
  if (saveBtn) saveBtn.textContent = `\u{1F4BE} Simpan PAM ${lbl}`;
  ipayReset();
}
```

(`ipayReset()` already calls `ipayFetchNextPamNo()` internally — no need to call it twice.)

- [ ] **Step 3: Add button-disable guard in `ipaySavePa()`**

Find the block just before the API call (line ~3530):
```javascript
  const res = await apiFetch("/payment-memo/ipay/save-pa", {
    method: "POST",
    body: JSON.stringify({ tab: type, tanggal, pam_no, keterangan, perusahaan, pillar, rows })
  });
  if (!res) return;
  const data = await res.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) {
    ipayReset();
```

Replace with:
```javascript
  const saveBtn2 = document.getElementById("ipay-save-btn");
  if (saveBtn2) saveBtn2.disabled = true;
  let res;
  try {
    res = await apiFetch("/payment-memo/ipay/save-pa", {
      method: "POST",
      body: JSON.stringify({ tab: type, tanggal, pam_no, keterangan, perusahaan, pillar, rows })
    });
  } finally {
    if (saveBtn2) saveBtn2.disabled = false;
  }
  if (!res) return;
  const data = await res.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) {
    ipayReset();
```

- [ ] **Step 4: Fix format hint error message**

Find (line ~3489):
```javascript
    showToast("No. PAM tidak valid. Format: PAM-054-AGRI-06-2026", "error"); return;
```

Replace with:
```javascript
    showToast("No. PAM tidak valid. Format: PAM-054-ETF-06-2026", "error"); return;
```

- [ ] **Step 5: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "fix: PAM input regex ETF|APP|LAND|SETF, remove double fetch, btn guard, hint msg"
```

---

## Verification Checklist

After all tasks:

```
cd app && python -m pytest tests/ -v
```

Expected: All tests pass (minimum 3 new tests added).

Manual smoke test in browser:
1. Buka tab Input — pilih AGRI, set tanggal → field No. PAM terisi `PAM-XXX-ETF-MM-YYYY`
2. Pilih LAND → field terisi `PAM-XXX-LAND-MM-YYYY`
3. Isi baris siswa + amount → klik Simpan → lihat tab AGRI → hanya **1 record** muncul dengan total benar
4. Cek DB: `SELECT pam_no, total_amount FROM pam_records ORDER BY id DESC LIMIT 5;` — tidak ada duplikat dengan total=0
