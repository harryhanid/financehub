# Sahabat ETF Laporan Periode Column Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate the previously-blank "Periode" column in the Sahabat ETF report (Excel export and on-screen Laporan tab), computed from `siswa.angkatan` plus a jenjang-based duration for PENDIDIKAN or a flat 1 year for KESEHATAN.

**Architecture:** `build_report_data()` gains a per-siswa-row `periode_start`/`periode_end` pair, computed by a new pure function from data already available in the same query. `report_xlsx.py` and `sahabat_etf.js` each get a small, isolated change to render the two new values into their already-existing (Excel) or newly-added (on-screen) Periode column.

**Tech Stack:** Python (Flask service layer, openpyxl), vanilla JS.

**Spec:** `docs/superpowers/specs/2026-08-11-sahabat-etf-laporan-periode-design.md`

## Global Constraints

- Duration table (PENDIDIKAN): `{"SD": 6, "SMP": 3, "SMA": 3, "SMK": 3, "S1": 4, "S2": 2, "S3": 4}` (years).
- KESEHATAN duration is always 1 year, regardless of jenjang, using the same `angkatan` field.
- Missing `angkatan` or an unmapped jenjang → `periode_start`/`periode_end` are `None` (Python) / absent-or-falsy (JS), never a crash or a guessed value.
- Only individual siswa detail rows get Periode. Subtotal, section-total, recap, combined-total, grand-total, and pillar-breakdown rows never carry `periode_start`/`periode_end` keys.
- No new database columns, no migration — `siswa.angkatan` already exists and is already used elsewhere in this module.

---

## Task 1: `service.py` — compute periode per siswa row

**Files:**
- Modify: `app/modules/sahabat_etf/service.py`
- Test: `app/tests/test_sahabat_etf_service.py`

**Interfaces:**
- Produces: `build_report_data(company_id, report_year)`'s siswa-row dicts (inside `sections[i]["groups"][j]["siswa_rows"]`) now include `"periode_start"` and `"periode_end"` keys (int or `None`). Recap/subtotal/total dicts are unchanged (no new keys). No signature changes to any existing function.

- [ ] **Step 1: Write the failing tests**

First, extend the `_add_siswa` test helper to accept an `angkatan` parameter (default unchanged, so all existing call sites keep working):

Find in `app/tests/test_sahabat_etf_service.py`:
```python
def _add_siswa(code, nama, program="Sahabat ETF", company_id=COMPANY_ID, jenjang="S1"):
    add_siswa(company_id, {
        "code": code, "nama": nama, "jenjang": jenjang, "angkatan": 2024,
        "program": program, "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
```

Replace with:
```python
def _add_siswa(code, nama, program="Sahabat ETF", company_id=COMPANY_ID, jenjang="S1", angkatan=2024):
    add_siswa(company_id, {
        "code": code, "nama": nama, "jenjang": jenjang, "angkatan": angkatan,
        "program": program, "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
```

Then add these tests to the same file:

```python
def test_build_report_data_computes_periode_for_pendidikan_siswa():
    _add_siswa("9995001", "Siswa S1", jenjang="S1", angkatan=2023)
    add_budget_batch(COMPANY_ID, "9995001", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])

    data = build_report_data(COMPANY_ID, 2026)
    row = next(s for s in data["sections"] if s["key"] == "PENDIDIKAN")["groups"][0]["siswa_rows"][0]
    assert row["periode_start"] == 2023
    assert row["periode_end"] == 2027  # S1 = 4 tahun


def test_build_report_data_computes_periode_for_kesehatan_siswa():
    _add_siswa("9995002", "Siswa Sehat", jenjang="SETF", angkatan=2026)
    add_budget_batch(COMPANY_ID, "9995002", "2026-01-10", "SETF",
        [{"cat1": "By Medical", "cat2": "Rawat Inap", "amount": 500000}])

    data = build_report_data(COMPANY_ID, 2026)
    row = next(s for s in data["sections"] if s["key"] == "KESEHATAN")["groups"][0]["siswa_rows"][0]
    assert row["periode_start"] == 2026
    assert row["periode_end"] == 2027  # Kesehatan = 1 tahun


def test_build_report_data_periode_blank_when_angkatan_missing():
    _add_siswa("9995003", "Siswa Tanpa Angkatan", jenjang="SD", angkatan=None)
    add_budget_batch(COMPANY_ID, "9995003", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])

    data = build_report_data(COMPANY_ID, 2026)
    row = next(s for s in data["sections"] if s["key"] == "PENDIDIKAN")["groups"][0]["siswa_rows"][0]
    assert row["periode_start"] is None
    assert row["periode_end"] is None


def test_build_report_data_periode_blank_for_unmapped_jenjang():
    _add_siswa("9995004", "Siswa Jenjang Aneh", jenjang="D3", angkatan=2024)
    add_budget_batch(COMPANY_ID, "9995004", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])

    data = build_report_data(COMPANY_ID, 2026)
    row = next(s for s in data["sections"] if s["key"] == "PENDIDIKAN")["groups"][0]["siswa_rows"][0]
    assert row["periode_start"] is None
    assert row["periode_end"] is None


def test_build_report_data_recap_has_no_periode_keys():
    _add_siswa("9995005", "Siswa Recap", jenjang="S1", angkatan=2023)
    add_budget_batch(COMPANY_ID, "9995005", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])

    data = build_report_data(COMPANY_ID, 2026)
    pend = next(s for s in data["sections"] if s["key"] == "PENDIDIKAN")
    recap_row = pend["recap"][0]
    assert "periode_start" not in recap_row
    assert "periode_end" not in recap_row
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_sahabat_etf_service.py -k "periode or recap_has_no_periode" -v`
Expected: FAIL — `KeyError: 'periode_start'` on the siswa-row assertions (the key doesn't exist yet).

- [ ] **Step 3: Add `s.angkatan` to `_fetch_report_rows()`'s two queries**

Find (in `app/modules/sahabat_etf/service.py`):
```python
def _fetch_report_rows(company_id: int):
    """Raw budget + payment rows (all years) for Sahabat ETF siswa, tagged with
    section/subgroup keys. Returns (budget_rows, payment_rows) as lists of dict."""
    conn = get_conn()
    budget_rows = conn.execute(
        """
        SELECT s.nama AS nama, s.jenjang AS jenjang, b.cat1 AS cat1, b.cat2 AS cat2,
               b.pillar AS pillar, CAST(strftime('%Y', b.tanggal) AS INTEGER) AS tahun,
               b.amount AS amount
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ? AND b.tanggal IS NOT NULL AND b.tanggal != ''
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    payment_rows = conn.execute(
        """
        SELECT s.nama AS nama, s.jenjang AS jenjang, p.cat1 AS cat1, p.cat2 AS cat2,
               p.pillar AS pillar, p.status AS status,
               CAST(strftime('%Y', p.tanggal) AS INTEGER) AS tahun, p.amount AS amount
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.tanggal IS NOT NULL AND p.tanggal != ''
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    conn.close()
    return [dict(r) for r in budget_rows], [dict(r) for r in payment_rows]
```

Replace with:
```python
def _fetch_report_rows(company_id: int):
    """Raw budget + payment rows (all years) for Sahabat ETF siswa, tagged with
    section/subgroup keys. Returns (budget_rows, payment_rows) as lists of dict."""
    conn = get_conn()
    budget_rows = conn.execute(
        """
        SELECT s.nama AS nama, s.jenjang AS jenjang, s.angkatan AS angkatan,
               b.cat1 AS cat1, b.cat2 AS cat2,
               b.pillar AS pillar, CAST(strftime('%Y', b.tanggal) AS INTEGER) AS tahun,
               b.amount AS amount
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ? AND b.tanggal IS NOT NULL AND b.tanggal != ''
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    payment_rows = conn.execute(
        """
        SELECT s.nama AS nama, s.jenjang AS jenjang, s.angkatan AS angkatan,
               p.cat1 AS cat1, p.cat2 AS cat2,
               p.pillar AS pillar, p.status AS status,
               CAST(strftime('%Y', p.tanggal) AS INTEGER) AS tahun, p.amount AS amount
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.tanggal IS NOT NULL AND p.tanggal != ''
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    conn.close()
    return [dict(r) for r in budget_rows], [dict(r) for r in payment_rows]
```

- [ ] **Step 4: Add the duration table and `_compute_periode()` helper**

Find (in `app/modules/sahabat_etf/service.py`):
```python
def _row_subgroup(section: str, row: dict) -> str:
    if section == "KESEHATAN":
        return row["cat2"] or "(Tanpa Kategori)"
    return row["jenjang"] or "(Tanpa Jenjang)"
```

Add immediately after it:
```python
_JENJANG_DURASI = {"SD": 6, "SMP": 3, "SMA": 3, "SMK": 3, "S1": 4, "S2": 2, "S3": 4}
_KESEHATAN_DURASI = 1


def _compute_periode(section_key: str, jenjang: str, angkatan) -> tuple:
    if not angkatan:
        return None, None
    if section_key == "KESEHATAN":
        return angkatan, angkatan + _KESEHATAN_DURASI
    durasi = _JENJANG_DURASI.get(jenjang)
    return (angkatan, angkatan + durasi) if durasi else (None, None)
```

- [ ] **Step 5: Track `angkatan` per bucket in `_build_buckets()`**

Find:
```python
    def bucket(section, subgroup, nama):
        key = (section, subgroup, nama)
        if key not in buckets:
            buckets[key] = {"cur": _empty_metrics(), "cum": _empty_metrics(), "pillars": set()}
        return buckets[key]

    for r in budget_rows:
        section  = _row_section(r["cat1"])
        subgroup = _row_subgroup(section, r)
        tahun    = r["tahun"]
        amount   = float(r["amount"] or 0)
        b = bucket(section, subgroup, r["nama"])
        b["pillars"].add(r["pillar"] or "")
        if tahun == report_year:
            _add_metrics(b["cur"], plafon=amount)
        if tahun is not None and tahun <= report_year:
            _add_metrics(b["cum"], plafon=amount)

    for r in payment_rows:
        section  = _row_section(r["cat1"])
        subgroup = _row_subgroup(section, r)
        tahun    = r["tahun"]
        amount   = float(r["amount"] or 0)
        dibayar  = amount if r["status"] == "complete" else 0.0
        b = bucket(section, subgroup, r["nama"])
        b["pillars"].add(r["pillar"] or "")
        if tahun == report_year:
            _add_metrics(b["cur"], klaim=amount, dibayar=dibayar)
        if tahun is not None and tahun <= report_year:
            _add_metrics(b["cum"], klaim=amount, dibayar=dibayar)

    return buckets
```

Replace with:
```python
    def bucket(section, subgroup, nama):
        key = (section, subgroup, nama)
        if key not in buckets:
            buckets[key] = {"cur": _empty_metrics(), "cum": _empty_metrics(), "pillars": set(), "angkatan": None}
        return buckets[key]

    for r in budget_rows:
        section  = _row_section(r["cat1"])
        subgroup = _row_subgroup(section, r)
        tahun    = r["tahun"]
        amount   = float(r["amount"] or 0)
        b = bucket(section, subgroup, r["nama"])
        b["pillars"].add(r["pillar"] or "")
        b["angkatan"] = r["angkatan"]
        if tahun == report_year:
            _add_metrics(b["cur"], plafon=amount)
        if tahun is not None and tahun <= report_year:
            _add_metrics(b["cum"], plafon=amount)

    for r in payment_rows:
        section  = _row_section(r["cat1"])
        subgroup = _row_subgroup(section, r)
        tahun    = r["tahun"]
        amount   = float(r["amount"] or 0)
        dibayar  = amount if r["status"] == "complete" else 0.0
        b = bucket(section, subgroup, r["nama"])
        b["pillars"].add(r["pillar"] or "")
        b["angkatan"] = r["angkatan"]
        if tahun == report_year:
            _add_metrics(b["cur"], klaim=amount, dibayar=dibayar)
        if tahun is not None and tahun <= report_year:
            _add_metrics(b["cum"], klaim=amount, dibayar=dibayar)

    return buckets
```

- [ ] **Step 6: Populate `periode_start`/`periode_end` in `_build_section()`'s siswa rows**

Find:
```python
        for nama in namas:
            b = buckets[(section_key, subgroup, nama)]
            siswa_rows.append({
                "nama": nama, "pillar": _pillar_label(b["pillars"]),
                "cur": b["cur"], "cum": b["cum"],
            })
```

Replace with:
```python
        for nama in namas:
            b = buckets[(section_key, subgroup, nama)]
            periode_start, periode_end = _compute_periode(section_key, subgroup, b["angkatan"])
            siswa_rows.append({
                "nama": nama, "pillar": _pillar_label(b["pillars"]),
                "cur": b["cur"], "cum": b["cum"],
                "periode_start": periode_start, "periode_end": periode_end,
            })
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_sahabat_etf_service.py -k "periode or recap_has_no_periode" -v`
Expected: PASS (5 tests)

- [ ] **Step 8: Run the full service test file to confirm no regressions**

Run: `cd app && python -m pytest tests/test_sahabat_etf_service.py -v`
Expected: all tests PASS

- [ ] **Step 9: Commit**

```bash
cd /c/Financehub
git add app/modules/sahabat_etf/service.py app/tests/test_sahabat_etf_service.py
git commit -m "feat: compute Periode (angkatan + jenjang duration) for Sahabat ETF report siswa rows"
```

---

## Task 2: `report_xlsx.py` — write Periode into the Excel export

**Files:**
- Modify: `app/modules/sahabat_etf/report_xlsx.py`
- Test: `app/tests/test_sahabat_etf_report_xlsx.py`

**Interfaces:**
- Consumes: `siswa_row["periode_start"]` / `siswa_row["periode_end"]` (Task 1) — may be absent or `None` in test fixtures that don't set them (existing fixtures), must be handled without crashing.
- Produces: no signature changes — `build_report_workbook(data)` now additionally writes the C/E columns (already reserved via `_COL["periode_start"]`/`_COL["periode_end"]`) for siswa rows that have periode data.

- [ ] **Step 1: Write the failing tests**

Add to `app/tests/test_sahabat_etf_report_xlsx.py`:

```python
def test_build_report_workbook_writes_periode_for_siswa_row():
    data = _sample_data_with_content()
    data["sections"][0]["groups"][0]["siswa_rows"][0]["periode_start"] = 2026
    data["sections"][0]["groups"][0]["siswa_rows"][0]["periode_end"] = 2032
    xlsx_bytes = build_report_workbook(data)
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active

    values = {}
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        for cell in row:
            if cell.value is not None:
                values.setdefault(cell.row, {})[cell.column_letter] = cell.value
    richard_row = next(r for r, v in values.items() if v.get("B") == "Richard Widjaja")
    assert values[richard_row]["C"] == 2026
    assert values[richard_row]["E"] == 2032


def test_build_report_workbook_leaves_periode_blank_when_missing():
    data = _sample_data_with_content()
    # periode_start/periode_end intentionally absent from the siswa row dict,
    # matching build_report_data()'s own output when angkatan is missing.
    xlsx_bytes = build_report_workbook(data)
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active

    values = {}
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        for cell in row:
            if cell.value is not None:
                values.setdefault(cell.row, {})[cell.column_letter] = cell.value
    richard_row = next(r for r, v in values.items() if v.get("B") == "Richard Widjaja")
    assert "C" not in values[richard_row]
    assert "E" not in values[richard_row]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_sahabat_etf_report_xlsx.py -k periode -v`
Expected: FAIL — `test_build_report_workbook_writes_periode_for_siswa_row` fails with a `KeyError` on `values[richard_row]["C"]` (nothing writes there yet).

- [ ] **Step 3: Write the periode values in `_write_section()`'s siswa-row loop**

Find (in `app/modules/sahabat_etf/report_xlsx.py`):
```python
        for siswa_row in group["siswa_rows"]:
            _apply_row_grid(ws, row, columns=_LABEL_COLUMNS)
            _apply_row_grid(ws, row, columns=["O"])
            _set(ws, f"B{row}", siswa_row["nama"], font=_FONT_NORMAL, align=_ALIGN_LEFT)
            _set(ws, f"F{row}", siswa_row["pillar"], font=_FONT_PILLAR, align=_ALIGN_CENTER)
            _write_metrics_row(ws, row, siswa_row, font=_FONT_NORMAL, fill=_FILL_LIGHT_BLUE)
            row += 1
```

Replace with:
```python
        for siswa_row in group["siswa_rows"]:
            _apply_row_grid(ws, row, columns=_LABEL_COLUMNS)
            _apply_row_grid(ws, row, columns=["O"])
            _set(ws, f"B{row}", siswa_row["nama"], font=_FONT_NORMAL, align=_ALIGN_LEFT)
            if siswa_row.get("periode_start") and siswa_row.get("periode_end"):
                _set(ws, f"C{row}", siswa_row["periode_start"], font=_FONT_NORMAL, align=_ALIGN_CENTER)
                _set(ws, f"E{row}", siswa_row["periode_end"], font=_FONT_NORMAL, align=_ALIGN_CENTER)
            _set(ws, f"F{row}", siswa_row["pillar"], font=_FONT_PILLAR, align=_ALIGN_CENTER)
            _write_metrics_row(ws, row, siswa_row, font=_FONT_NORMAL, fill=_FILL_LIGHT_BLUE)
            row += 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_sahabat_etf_report_xlsx.py -k periode -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full report_xlsx test file to confirm no regressions**

Run: `cd app && python -m pytest tests/test_sahabat_etf_report_xlsx.py -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
cd /c/Financehub
git add app/modules/sahabat_etf/report_xlsx.py app/tests/test_sahabat_etf_report_xlsx.py
git commit -m "feat: write Periode column into Sahabat ETF Excel report for siswa rows"
```

---

## Task 3: `sahabat_etf.js` — add Periode column to the on-screen Laporan tab

**Files:**
- Modify: `app/static/js/sahabat_etf.js`
- Test: `app/tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Consumes: `row.periode_start` / `row.periode_end` from the `/api/report` JSON response (Task 1's `build_report_data()` output, unchanged shape otherwise).
- Produces: `setfLaporanPeriodeText(row)` (new helper) — used by `setfLaporanNamaRow()`; `setfLaporanHeaderRow()` and `setfLaporanLabelRow()` column counts change (3 non-metric columns instead of 2), consumed only within this file.

- [ ] **Step 1: Confirm current state before editing**

Run: `cd app && grep -n "colspan=\"2\"" static/js/sahabat_etf.js`
Expected: one match, inside `setfLaporanLabelRow` — confirms the exact string this task will change.

- [ ] **Step 2: Add the Periode column to the header row**

Find (in `app/static/js/sahabat_etf.js`):
```javascript
function setfLaporanHeaderRow(reportYear) {
  return '<tr class="setf-laporan-header">' +
    '<th rowspan="2">Nama</th><th rowspan="2">Pillar</th>' +
    '<th colspan="4">Tahun ' + reportYear + '</th>' +
    '<th colspan="4">S/D Tahun ' + reportYear + '</th></tr>' +
    '<tr class="setf-laporan-header">' +
    '<th>Plafon</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th>' +
    '<th>Plafon</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th></tr>';
}
```

Replace with:
```javascript
function setfLaporanHeaderRow(reportYear) {
  return '<tr class="setf-laporan-header">' +
    '<th rowspan="2">Nama</th><th rowspan="2">Periode</th><th rowspan="2">Pillar</th>' +
    '<th colspan="4">Tahun ' + reportYear + '</th>' +
    '<th colspan="4">S/D Tahun ' + reportYear + '</th></tr>' +
    '<tr class="setf-laporan-header">' +
    '<th>Plafon</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th>' +
    '<th>Plafon</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th></tr>';
}
```

- [ ] **Step 3: Add the Periode cell to siswa/recap rows**

Find:
```javascript
function setfLaporanNamaRow(row, cls) {
  return '<tr class="' + cls + '"><td>' + row.nama + '</td><td>' + row.pillar + '</td>' +
    setfLaporanMetricsCells(row) + '</tr>';
}
```

Replace with:
```javascript
function setfLaporanPeriodeText(row) {
  if (!row.periode_start || !row.periode_end) return '';
  return row.periode_start + ' - ' + row.periode_end;
}

function setfLaporanNamaRow(row, cls) {
  return '<tr class="' + cls + '"><td>' + row.nama + '</td><td>' + setfLaporanPeriodeText(row) + '</td><td>' + row.pillar + '</td>' +
    setfLaporanMetricsCells(row) + '</tr>';
}
```

- [ ] **Step 4: Widen the label-row colspan to cover the new column**

Find:
```javascript
function setfLaporanLabelRow(label, metrics, cls) {
  return '<tr class="' + cls + '"><td colspan="2">' + label + '</td>' +
    setfLaporanMetricsCells(metrics) + '</tr>';
}
```

Replace with:
```javascript
function setfLaporanLabelRow(label, metrics, cls) {
  return '<tr class="' + cls + '"><td colspan="3">' + label + '</td>' +
    setfLaporanMetricsCells(metrics) + '</tr>';
}
```

- [ ] **Step 5: Structural check**

Run:
```bash
cd app && python3 -c "
src = open('static/js/sahabat_etf.js', encoding='utf-8').read()
assert 'function setfLaporanPeriodeText' in src
assert '<th rowspan=\"2\">Periode</th>' in src
assert 'colspan=\"3\"' in src
assert 'colspan=\"2\"' not in src[src.index('setfLaporanHeaderRow'):src.index('function setfRenderLaporanSection')]
print('JS_STRUCTURAL_OK')
"
```
Expected: `JS_STRUCTURAL_OK`

- [ ] **Step 6: App-boot sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK`

- [ ] **Step 7: Commit**

```bash
cd /c/Financehub
git add app/static/js/sahabat_etf.js
git commit -m "feat: show Periode column in Sahabat ETF on-screen Laporan tab"
```

---

## Task 4: Final verification

**Files:**
- None modified (verification only)

**Interfaces:**
- Consumes: everything from Tasks 1-3

- [ ] **Step 1: Full Sahabat ETF test suite**

Run: `cd app && python -m pytest tests/test_sahabat_etf_service.py tests/test_sahabat_etf_report_xlsx.py tests/test_sahabat_etf_routes.py -v`
Expected: all tests pass.

- [ ] **Step 2: Manual browser check (if a preview session with non-production data is available)**

Open the Sahabat ETF Laporan tab. Confirm: a "Periode" column appears between Nama and Pillar for every siswa row, showing e.g. "2023 - 2027" for an S1 student entered in 2023; recap/subtotal/total rows show no periode text and their label cell still spans correctly (no visual column misalignment). Download the Excel export for the same year and confirm the Periode column (between Deskripsi and Pillar) shows the same values. Skip if no preview/browser session with non-production data is available — do not block on it.

- [ ] **Step 3: Confirm zero blast radius outside Sahabat ETF**

Run: `cd /c/Financehub && git diff --stat HEAD~3 -- app/templates/beasiswa/index.html app/static/js/dashboard_beasiswa.js`

(Adjust `HEAD~3` if the actual number of commits from this plan's Tasks 1-3 differs.)

Expected: empty output for both files, evaluated against **committed** state only.
