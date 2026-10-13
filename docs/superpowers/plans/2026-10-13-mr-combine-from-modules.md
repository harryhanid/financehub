# MR GL Combine / Append1 dari modul GL dan Sponsorship — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modul Management Report punya dua tab baru, **GL Combine** (17 kolom) dan **Append1** (13 kolom), yang dibentuk dari GL SMT, GL ETF (modul General Ledger) dan Sponsorship SMT (modul Sponsorship), dengan filter cutoff bulan kumulatif; fitur upload/sync Excel yang sudah ada di modul MR tetap utuh.

**Architecture:** Logika pemetaan COA/CC, pembentuk baris, dan daftar kolom dipindah (`git mv`) dari `modules/general_ledger/` ke `modules/management_report/`. Adaptor sumber baru (`combine_sources.py`) membaca GL dan Sponsorship; builder tiga sumber (`combine_rows.py`) menghitung baris saat halaman dibuka. Dua halaman baru di blueprint MR memakai bilah tab berbasis tautan (`mr-linktab`) yang tidak bentrok dengan JS `initTabs`. Tab MR lama di modul GL dihapus di akhir.

**Tech Stack:** Flask, SQLite (`database.get_conn`), `pyxlsb`, `decimal`, Jinja, pytest.

**Spec:** `docs/superpowers/specs/2026-10-13-mr-combine-from-modules-design.md` (lihat catatan "Penyimpangan dari spec" di bawah).

## Global Constraints

- Semua path relatif terhadap `C:\Financehub\app`; perintah dijalankan dari folder itu. Repo git: `C:\Financehub`.
- Bekerja langsung di master (tanpa worktree). Working tree berisi perubahan pengguna yang belum ter-commit (`app/app.py`, `app/static/js/app.js`, dll.): **jangan** `git add -A` / `git commit -a`; commit hanya file yang Anda sentuh (`git mv` otomatis men-stage rename; tetap `git add` file yang diedit). Jangan mengubah atau men-stage `app/app.py` dan `app/static/js/app.js`.
- Pesan commit diakhiri baris `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- **Fitur lama modul MR tidak boleh berubah perilakunya:** `POST /management-report/sync`, snapshot `mr_upload`/`mr_append`, tab Data Sync / Report / HO Report, export BGT. Semua tes `tests/test_mr_*.py` harus lulus **tanpa diubah**. Perubahan pada `templates/management_report/index.html` dan `modules/management_report/routes.py` hanya menambah (tautan tab baru, route baru, filter template baru).
- Modul Sponsorship (`modules/sponsorship/`) dan konstanta `SPONSORSHIP_MR_*` di `config.py` tidak diubah.
- Jangan membuat tab baru ikut dalam selektor JS `.tabs .tab-btn` (di `static/js/app.js`): tautan tab baru memakai kelas `mr-linktab`, bukan `tab-btn`.
- Filter baris GL: Account Management diawali 6–9 dan DEBIT − CREDIT tidak nol. ACT = (nominal)/1.000.000, 1 desimal, setengah ke genap setelah normalisasi 15 digit signifikan (`excel_round_mio`). Pembulatan ini sudah ada, jangan diubah.
- Cutoff kumulatif: tahun terpilih dan bulan ≤ bulan terpilih. Penomoran New Code dihitung atas **semua** baris bentukan (urutan SMT → ETF → Sponsor) sebelum filter apa pun.
- Parameter tidak valid (`yy`, `mm`, `page`, `cc`, `source`) kembali ke default dengan HTTP 200; semua nilai yang ditampilkan di-escape; sync pemetaan hanya admin dan hanya `.xlsb`, kesalahan sebagai JSON.
- Workbook di drive Y: diperlakukan read-only (hanya disalin ke folder temp dan dibaca dengan pyxlsb).
- Tes memakai `tests/conftest.py` (DB uji terisolasi, file DB bersama `tests/test_finance_hub.db`). **Jangan menjalankan dua proses pytest bersamaan.** Login uji: `POST /auth/login` admin/Admin@123 lalu `POST /select-company`.

## Penyimpangan dari spec

Spec menyebut konstanta `MR_SPONSOR_COST_CENTER2` dan `MR_SPONSOR_CC1`. Pemeriksaan data menunjukkan sheet `CC` sudah memetakan `POSPON` ke `$POCCOM` dengan urutan 5, dan tabel `sponsorship_transaksi` membawa kolom `coa` (`701078002`), `cc` (`POSPON`), `source` (`Sponsor`). Maka:
- baris Sponsor memakai `coa` dan `cc` **dari baris Sponsorship**; COST CENTER2 dan CC1 dicari lewat **pemetaan CC yang sama dengan GL** (bukan konstanta);
- `config.py` hanya mendapat cadangan bila kolom kosong: `MR_SPONSOR_ACCOUNT = "701078002"`, `MR_SPONSOR_COST_CENTER = "POSPON"`, `MR_SPONSOR_SOURCE = "Sponsor"`.
Task 2 memperbarui spec agar sesuai.

## Review Focus

- Baris Sponsorship dengan `tanggal_form_sponsor` kosong/tidak valid, `perihal` NULL, atau `amount_request` NULL: dilewati/dikosongkan tanpa error. Dites di Task 2.
- Tabel `companies` tanpa baris `SMT`: adaptor Sponsor mengembalikan `[]`, halaman tetap jalan. Dites di Task 2.
- Filter Source tidak valid, atau dikombinasikan dengan cutoff/pencarian: kembali ke "Semua"; New Code tidak berubah saat Source/CC/cutoff diganti. Dites di Task 3.
- Fitur lama modul MR tetap utuh: seluruh `tests/test_mr_*.py` lulus tanpa diubah, dan di `index.html` tautan tab baru tidak memakai kelas `tab-btn`. Dites di Task 3.
- Setelah tab MR di modul GL dihapus, tab GL SMT/ETF/SETF tetap berfungsi dan `/general-ledger/mr` menghasilkan 404. Dites di Task 4.

---

### Task 1: Pindahkan logika bersama ke modul MR (mekanis, semua tes tetap hijau)

**Files:**
- Move: `modules/general_ledger/coa_map.py` → `modules/management_report/coa_map.py`
- Move: `modules/general_ledger/mr_rows.py` → `modules/management_report/combine_rows.py`
- Move: `modules/general_ledger/mr_columns.py` → `modules/management_report/combine_columns.py`
- Modify: `modules/general_ledger/mr_report.py` (impor `UNMAPPED`), `modules/general_ledger/routes.py` (impor)
- Move tes: `tests/test_gl_coa_map.py` → `tests/test_mrc_coa_map.py`, `tests/test_gl_mr_rows.py` → `tests/test_mrc_rows.py`
- Modify tes: `tests/test_gl_mr_routes.py`, `tests/test_gl_mr_report.py`, `tests/test_gl_mr_real_file.py` (hanya jalur impor)

**Interfaces:**
- Produces: modul `modules.management_report.coa_map` (API sama persis dengan sebelumnya: `get_map`, `get_cc_map`, `last_sync`, `sync_coa`, `read_mapping_sheets`, `read_coa_sheet`, `CoaParseError`, …), `modules.management_report.combine_rows` (fungsi yang sama, termasuk `build_mr_rows` untuk sementara; diubah di Task 2), `modules.management_report.combine_columns` (`COMBINE`, `APPEND1`, `TABLES`, `resolve_table`, …).

- [ ] **Step 1: Pastikan baseline hijau**

Run: `python -m pytest tests/test_gl_parser.py tests/test_gl_sync.py tests/test_gl_service.py tests/test_gl_routes.py tests/test_gl_coa_map.py tests/test_gl_mr_rows.py tests/test_gl_mr_report.py tests/test_gl_mr_routes.py tests/test_gl_mr_real_file.py tests/test_gl_real_file.py tests/test_dashboard.py tests/test_mr_routes.py tests/test_mr_service.py tests/test_mr_sync.py -q -W ignore -p no:cacheprovider`
Expected: semua PASS (catat jumlahnya).

- [ ] **Step 2: Pindahkan file**

```bash
git mv modules/general_ledger/coa_map.py modules/management_report/coa_map.py
git mv modules/general_ledger/mr_rows.py modules/management_report/combine_rows.py
git mv modules/general_ledger/mr_columns.py modules/management_report/combine_columns.py
git mv tests/test_gl_coa_map.py tests/test_mrc_coa_map.py
git mv tests/test_gl_mr_rows.py tests/test_mrc_rows.py
```

- [ ] **Step 3: Perbarui impor**

Cari semua rujukan lama:

```bash
grep -rn "general_ledger import coa_map\|general_ledger.coa_map\|general_ledger import mr_rows\|general_ledger.mr_rows\|general_ledger import mr_columns\|general_ledger.mr_columns\|mr_rows as\|import mr_rows\|import mr_columns\|import coa_map" modules tests | grep -v __pycache__
```

Ganti setiap rujukan:
- `modules.general_ledger.coa_map` / `from modules.general_ledger import coa_map` → `modules.management_report.coa_map` / `from modules.management_report import coa_map`
- `modules.general_ledger.mr_rows` → `modules.management_report.combine_rows` (di `routes.py` GL: `from modules.management_report import combine_rows as mr_rows`, nama lokal `mr_rows` dipertahankan agar sisa kode tidak berubah)
- `modules.general_ledger.mr_columns` → `modules.management_report.combine_columns` (di `routes.py` GL: `from modules.management_report import combine_columns as mr_columns`)
- `modules/general_ledger/mr_report.py`: `from modules.general_ledger.mr_rows import UNMAPPED` → `from modules.management_report.combine_rows import UNMAPPED`.
- Di tes: `from modules.general_ledger import coa_map as cm` → `from modules.management_report import coa_map as cm`; `from modules.general_ledger import mr_rows as mr` → `from modules.management_report import combine_rows as mr`; di `tests/test_gl_mr_routes.py` ganti `from modules.general_ledger import coa_map` → `from modules.management_report import coa_map` dan tes yang memakai `gl_routes.coa_map` tetap benar karena `routes.py` GL mengimpor modul yang sama.
- Di `tests/test_gl_mr_real_file.py`: ganti impor `coa_map`/`mr_rows` ke lokasi baru.

Verifikasi tidak ada rujukan tersisa:

Run: `grep -rn "general_ledger.\(coa_map\|mr_rows\|mr_columns\)\|general_ledger import \(coa_map\|mr_rows\|mr_columns\)" modules tests | grep -v __pycache__`
Expected: tidak ada keluaran.

- [ ] **Step 4: Jalankan seluruh set tes dari Step 1 (dengan nama berkas baru)**

Run: `python -m pytest tests/test_gl_parser.py tests/test_gl_sync.py tests/test_gl_service.py tests/test_gl_routes.py tests/test_mrc_coa_map.py tests/test_mrc_rows.py tests/test_gl_mr_report.py tests/test_gl_mr_routes.py tests/test_gl_mr_real_file.py tests/test_gl_real_file.py tests/test_dashboard.py tests/test_mr_routes.py tests/test_mr_service.py tests/test_mr_sync.py -q -W ignore -p no:cacheprovider`
Expected: semua PASS dengan jumlah yang sama seperti Step 1.

- [ ] **Step 5: Commit**

```bash
git add modules/management_report/coa_map.py modules/management_report/combine_rows.py modules/management_report/combine_columns.py modules/general_ledger/mr_report.py modules/general_ledger/routes.py tests/test_mrc_coa_map.py tests/test_mrc_rows.py tests/test_gl_mr_routes.py tests/test_gl_mr_report.py tests/test_gl_mr_real_file.py
git commit -m "refactor(mr): move COA mapping, row builder and column specs into the Management Report module

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Sumber Sponsorship dan builder tiga sumber

**Files:**
- Modify: `config.py` (tambah tiga konstanta cadangan)
- Create: `modules/management_report/combine_sources.py`
- Modify: `modules/management_report/combine_rows.py` (ganti nama `build_mr_rows` → `build_combine_rows`, tambah cabang Sponsor)
- Modify: `modules/general_ledger/routes.py` (hanya nama fungsi yang dipanggil: `mr_rows.build_combine_rows`)
- Modify tes: `tests/test_mrc_rows.py` (ganti nama + tes baru), `tests/test_gl_mr_routes.py`, `tests/test_gl_mr_real_file.py` (hanya nama fungsi)
- Create tes: `tests/test_mrc_sources.py`
- Modify: `docs/superpowers/specs/2026-10-13-mr-combine-from-modules-design.md` (sesuaikan bagian "Aturan baris → Sponsor" dan "config.py" dengan "Penyimpangan dari spec" di plan ini)

**Interfaces:**
- Consumes: `coa_map` dari Task 1, `general_ledger.service.load_mr_source(entity)`, `sponsorship.service.list_transaksi(company_id, filters=None)`.
- Produces:
  - `combine_sources.gl_rows(entity: str) -> list[dict]` (kunci `acc_management, tgl, allocation_memo, budget_activity, job_name, debit_credit, id_no`)
  - `combine_sources.smt_company_id() -> int | None`
  - `combine_sources.sponsor_rows_from(rows: list[dict]) -> list[dict]` (fungsi murni; masukan: baris dengan kunci `id, tanggal_form_sponsor, perihal, amount_request, coa, cc`), keluaran: dict `{"tgl","perihal","amount","coa","cc"}` terurut `(tanggal_form_sponsor, id)` naik
  - `combine_sources.sponsor_rows() -> list[dict]` (membungkus DB)
  - `combine_rows.build_combine_rows(source_rows: dict, coa_map: dict, cc_map: dict | None = None) -> MrBuild`; `source_rows` berkunci `"SMT"`, `"ETF"` (baris GL) dan `"Sponsor"` (keluaran `sponsor_rows`). Baris hasil memakai kunci yang sama seperti sebelumnya.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_mrc_sources.py
from database import get_conn
from modules.general_ledger import service as gl_service
from modules.management_report import combine_sources as src
from tests.test_gl_sync import mkrow

LOG = dict(synced_by="u", filename="f", content_hash="h", rows_before=0, rows_after=1,
           total_debit=0, total_credit=0, dropped=0, summary={})


def insert_sponsor(company_id, tgl, perihal, amount, coa="701078002", cc="POSPON"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO sponsorship_transaksi (company_id, cat, description, tanggal_form_sponsor, cat1, cat2, "
        "cat3, lembaga_perorangan, perihal, amount_request, coa, cc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (company_id, "Event", "desc", tgl, "c1", "c2", "APP", "lembaga", perihal, amount, coa, cc))
    conn.commit()
    conn.close()


def test_smt_company_id_is_looked_up_by_code():
    conn = get_conn()
    expected = conn.execute("SELECT id FROM companies WHERE code='SMT'").fetchone()["id"]
    conn.close()
    assert src.smt_company_id() == expected


def test_sponsor_rows_only_smt_ordered_by_form_date_then_id():
    smt = src.smt_company_id()
    other = [r for r in (1, 2, 3) if r != smt][0]
    insert_sponsor(smt, "2026-02-10", "B", 20.0)
    insert_sponsor(smt, "2026-01-05", "A2", 10.0)
    insert_sponsor(smt, "2026-01-05", "A1", 5.0)          # same date: id order
    insert_sponsor(other, "2026-01-01", "ETF row", 99.0)  # other company: excluded
    rows = src.sponsor_rows()
    assert [(r["tgl"], r["perihal"], r["amount"]) for r in rows] == [
        ("2026-01-05", "A2", 10.0), ("2026-01-05", "A1", 5.0), ("2026-02-10", "B", 20.0)]
    assert rows[0]["coa"] == "701078002" and rows[0]["cc"] == "POSPON"


def test_sponsor_rows_include_every_year():
    smt = src.smt_company_id()
    insert_sponsor(smt, "2025-12-31", "old", 1.0)
    insert_sponsor(smt, "2026-01-01", "new", 2.0)
    assert [r["perihal"] for r in src.sponsor_rows()] == ["old", "new"]


def test_sponsor_rows_from_handles_null_perihal_and_amount():
    out = src.sponsor_rows_from([
        {"id": 1, "tanggal_form_sponsor": "2026-01-01", "perihal": None, "amount_request": None,
         "coa": None, "cc": None}])
    assert out == [{"tgl": "2026-01-01", "perihal": "", "amount": 0.0, "coa": "", "cc": ""}]


def test_sponsor_rows_empty_when_smt_company_is_missing(monkeypatch):
    monkeypatch.setattr(src, "smt_company_id", lambda: None)
    assert src.sponsor_rows() == []


def test_gl_rows_delegates_to_the_general_ledger_service():
    gl_service.replace_all("smt", [mkrow(acc_management="6-1810", debit_credit=5.0,
                                         allocation_memo="m", job_name="J")], LOG)
    rows = src.gl_rows("smt")
    assert len(rows) == 1 and rows[0]["acc_management"] == "6-1810" and rows[0]["id_no"] == "GJ-1"
```

Tambahkan di `tests/test_mrc_rows.py` (ganti nama pemanggilan `build_mr_rows` → `build_combine_rows` di seluruh file, lalu tambah):

```python
SP = {"tgl": "2026-01-19", "perihal": "Prasasti Membership", "amount": 500000000.0,
      "coa": "701078002", "cc": "POSPON"}
CCMAP = {"POSPON": {"total": "$POCCOM", "seq": 5, "description": "SMT - Sponshorship"}}


def build_all(smt=(), etf=(), sponsor=(), cc_map=None):
    return mr.build_combine_rows({"SMT": list(smt), "ETF": list(etf), "Sponsor": list(sponsor)},
                                 CMAP, CCMAP if cc_map is None else cc_map)


def test_sponsor_row_follows_the_workbook_format():
    res = build_all(sponsor=[SP])
    assert res.skipped_date == 0
    assert res.rows == [{
        "coa": "701078002", "mm": 1, "yy": 2026, "cc": "POSPON", "category": "",
        "activity": "", "description": "- Act 2026 : Prasasti Membership Month : 1",
        "custom": "3", "mm1": 1, "pta": 0.0, "bgt": 0.0, "act": 500.0, "source": "Sponsor",
        "account": "701078002", "unmapped": False, "id_no": "", "tgl": "2026-01-19",
        "allocation_memo": "Prasasti Membership", "debit_credit": 500000000.0,
        "cost_center2": "$POCCOM", "cc0": "26", "cc1": 5, "bc1": "", "new_code": "A26-51",
        "cc_unmapped": False}]


def test_sponsor_new_codes_count_per_year_and_after_gl_rows():
    rows = build_all(
        smt=[g(tgl="2026-01-15")],
        sponsor=[dict(SP, tgl="2026-01-19"), dict(SP, tgl="2026-02-01"), dict(SP, tgl="2027-01-02")]).rows
    assert rows[0]["source"] == "SMT" and rows[0]["new_code"].endswith("-1")
    assert [(r["source"], r["new_code"]) for r in rows[1:]] == [
        ("Sponsor", "A26-51"), ("Sponsor", "A26-52"), ("Sponsor", "A27-51")]


def test_gl_rows_do_not_disturb_sponsor_numbering():
    only = build_all(sponsor=[SP, dict(SP, tgl="2026-03-01")]).rows
    mixed = build_all(smt=[g(), g()], etf=[g("6-2190", amount=30000.0)],
                      sponsor=[SP, dict(SP, tgl="2026-03-01")]).rows
    assert [r["new_code"] for r in only] == ["A26-51", "A26-52"]
    assert [r["new_code"] for r in mixed if r["source"] == "Sponsor"] == ["A26-51", "A26-52"]


def test_sponsor_cost_center_uses_the_cc_mapping_and_flags_when_missing():
    res = build_all(sponsor=[SP], cc_map={})
    assert res.rows[0]["cost_center2"] == "" and res.rows[0]["cc1"] == 0
    assert res.rows[0]["cc_unmapped"] is True


def test_sponsor_blank_coa_and_cc_fall_back_to_config():
    res = build_all(sponsor=[dict(SP, coa="", cc="")])
    assert res.rows[0]["coa"] == "701078002" and res.rows[0]["cc"] == "POSPON"


def test_sponsor_rows_with_invalid_date_are_skipped_and_counted():
    res = build_all(sponsor=[dict(SP, tgl=None), dict(SP, tgl="garbage"), SP])
    assert len(res.rows) == 1 and res.skipped_date == 2


def test_sponsor_empty_perihal_and_zero_amount_are_kept():
    res = build_all(sponsor=[dict(SP, perihal="", amount=0.0)])
    assert res.rows[0]["description"] == "- Act 2026 :  Month : 1" and res.rows[0]["act"] == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_mrc_sources.py tests/test_mrc_rows.py -q -W ignore -p no:cacheprovider`
Expected: FAIL (impor `combine_sources` tidak ada; `build_combine_rows` tidak ada).

- [ ] **Step 3: Implementasi**

`config.py` (di bawah konstanta `SPONSORSHIP_MR_*`):

```python
# Management Report GL Combine — Sponsorship source (workbook format). Used only as fallbacks when the
# sponsorship_transaksi row has an empty coa/cc. See docs/superpowers/specs/2026-10-13-mr-combine-from-modules-design.md
MR_SPONSOR_ACCOUNT     = "701078002"
MR_SPONSOR_COST_CENTER = "POSPON"
MR_SPONSOR_SOURCE      = "Sponsor"
```

`modules/management_report/combine_sources.py`:

```python
"""Management Report: raw rows from the modules that feed GL Combine (read-only)."""
from database import get_conn
from modules.general_ledger import service as gl_service
from modules.sponsorship import service as sponsorship_service


def gl_rows(entity: str) -> list:
    """GL SMT / GL ETF rows that carry an amount (see general_ledger.service.load_mr_source)."""
    return gl_service.load_mr_source(entity)


def smt_company_id():
    conn = get_conn()
    try:
        row = conn.execute("SELECT id FROM companies WHERE code = 'SMT'").fetchone()
        return row["id"] if row else None
    finally:
        conn.close()


def sponsor_rows_from(rows: list) -> list:
    """Pure: reduce sponsorship_transaksi rows to what GL Combine needs, ordered by form date then id."""
    ordered = sorted(rows, key=lambda r: (r.get("tanggal_form_sponsor") or "", r.get("id") or 0))
    return [{"tgl": r.get("tanggal_form_sponsor"),
             "perihal": r.get("perihal") or "",
             "amount": float(r.get("amount_request") or 0.0),
             "coa": str(r.get("coa") or "").strip(),
             "cc": str(r.get("cc") or "").strip()} for r in ordered]


def sponsor_rows() -> list:
    """Sponsorship transactions of company SMT, every year, every status."""
    company_id = smt_company_id()
    if company_id is None:
        return []
    return sponsor_rows_from(sponsorship_service.list_transaksi(company_id))
```

`modules/management_report/combine_rows.py`: ubah `import` dan fungsi. Tambahkan `import config` di atas, ganti nama fungsi dan tambahkan cabang Sponsor setelah loop SMT/ETF (sebelum `return`):

```python
import config
...
def build_combine_rows(source_rows: dict, coa_map: dict, cc_map: dict = None) -> MrBuild:
    """Rows in GL Combine / Append1 shape from GL SMT, GL ETF and Sponsorship (in that order).
    `new_code` numbers run per (cc0, cc1, bc1) over ALL built rows, so apply any filter afterwards."""
    ... (isi lama untuk SMT dan ETF tetap sama persis) ...

    for r in source_rows.get("Sponsor", []):
        d = _parse_date(r.get("tgl"))
        if d is None:
            skipped += 1
            continue
        amount = float(r.get("amount") or 0.0)
        coa = str(r.get("coa") or "").strip() or config.MR_SPONSOR_ACCOUNT
        cc = str(r.get("cc") or "").strip() or config.MR_SPONSOR_COST_CENTER
        memo = r.get("perihal") or ""
        cc_entry = cc_map.get(cc) or {}
        seq = int(cc_entry.get("seq") or 0)
        total = cc_entry.get("total") or ""
        cc0 = f"{d.year % 100:02d}"
        group = (cc0, seq, "")
        counters[group] = counters.get(group, 0) + 1
        rows.append({
            "coa": coa, "mm": d.month, "yy": d.year, "cc": cc, "category": "", "activity": "",
            "description": f"- Act {d.year} : {memo} Month : {d.month}",
            "custom": "3", "mm1": d.month, "pta": 0.0, "bgt": 0.0,
            "act": excel_round_mio(amount), "source": config.MR_SPONSOR_SOURCE, "account": coa,
            "unmapped": False, "id_no": "", "tgl": d.isoformat(), "allocation_memo": memo,
            "debit_credit": amount, "cost_center2": total, "cc0": cc0, "cc1": seq, "bc1": "",
            "new_code": f"A{cc0}-{seq}{counters[group]}", "cc_unmapped": not total,
        })
    return MrBuild(rows, skipped)
```

Pemanggil lama: di `modules/general_ledger/routes.py` ganti `mr_rows.build_mr_rows(` → `mr_rows.build_combine_rows(`; di `tests/test_gl_mr_routes.py` dan `tests/test_gl_mr_real_file.py` ganti nama fungsi yang sama.

Perbarui spec: di `docs/superpowers/specs/2026-10-13-mr-combine-from-modules-design.md` bagian "Aturan baris → Sponsor" tulis bahwa `coa` dan `cc` berasal dari kolom `coa`/`cc` baris Sponsorship (cadangan dari konfigurasi bila kosong), dan COST CENTER2 / CC1 dicari lewat pemetaan CC; hapus `MR_SPONSOR_COST_CENTER2` dan `MR_SPONSOR_CC1` dari daftar konfigurasi.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_mrc_sources.py tests/test_mrc_rows.py tests/test_mrc_coa_map.py tests/test_gl_mr_routes.py tests/test_gl_mr_real_file.py -q -W ignore -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config.py modules/management_report/combine_sources.py modules/management_report/combine_rows.py modules/general_ledger/routes.py tests/test_mrc_sources.py tests/test_mrc_rows.py tests/test_gl_mr_routes.py tests/test_gl_mr_real_file.py ../docs/superpowers/specs/2026-10-13-mr-combine-from-modules-design.md
git commit -m "feat(mr): combine GL SMT, GL ETF and Sponsorship rows with workbook-format Sponsor rows

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Halaman GL Combine dan Append1 di modul MR

**Files:**
- Create: `modules/management_report/combine_query.py`
- Modify: `modules/management_report/routes.py` (impor, filter template, route baru)
- Create: `templates/management_report/combine.html`
- Create: `templates/management_report/_linktabs.html`
- Create: `static/css/mr_combine.css`
- Modify: `templates/management_report/index.html` (link CSS di blok `head`; dua tautan di blok `module_tabs`)
- Create tes: `tests/test_mrc_query.py`, `tests/test_mrc_routes.py`

**Interfaces:**
- Consumes: Task 1 & 2 (`coa_map`, `combine_columns`, `combine_rows.build_combine_rows/period_options/apply_cutoff/unmapped_summary/unmapped_cc_summary`, `combine_sources.gl_rows/sponsor_rows`).
- Produces:
  - `combine_query.SOURCES = ("SMT", "ETF", "Sponsor")`, `list_ccs(rows)`, `filter_source(rows, source)`, `query_data(rows, q=None, cc=None, source=None, page=1, per_page=100) -> dict` berkunci `rows, total, sum_act, sum_dc, page, pages, per_page`.
  - Endpoint `management_report.gl_combine` (`GET /management-report/gl-combine`), `management_report.append1_page` (`GET /management-report/append1`), `management_report.sync_mapping` (`POST /management-report/gl-combine/sync-mapping`). Parameter GET: `yy, mm, cc, source, q, page`.
  - Filter template `mc_num` (rupiah, titik ribuan), `mc_mio` (1 desimal, koma desimal, tidak pernah `-0,0`), `mc_date` (`2026-01-15` → `15/01/2026`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_mrc_query.py
from modules.management_report import combine_query as cq


def row(i, cc="AAA", source="SMT", mm=1, act=1.0, dc=1000000.0, **kw):
    r = {"coa": "70108100", "mm": mm, "yy": 2026, "cc": cc, "category": "10 - X", "activity": "Act",
         "description": f"row {i}", "custom": "3", "mm1": mm, "pta": 0.0, "bgt": 0.0, "act": act,
         "source": source, "account": "6-1810", "unmapped": False, "id_no": f"GJ-{i}", "tgl": "2026-01-15",
         "allocation_memo": f"memo {i}", "debit_credit": dc, "cost_center2": "$X", "cc0": "26", "cc1": 1,
         "bc1": "-10-", "new_code": f"A26-1-10-{i}", "cc_unmapped": False}
    r.update(kw)
    return r


ROWS = [row(i, cc="AAA" if i % 2 else "BBB", source=("SMT", "ETF", "Sponsor")[i % 3]) for i in range(1, 251)]


def test_list_ccs_sorted_unique():
    assert cq.list_ccs(ROWS) == ["AAA", "BBB"]


def test_pagination_keeps_build_order():
    r = cq.query_data(ROWS, page=1)
    assert r["total"] == 250 and r["pages"] == 3 and [x["id_no"] for x in r["rows"]][:3] == ["GJ-1", "GJ-2", "GJ-3"]
    assert len(cq.query_data(ROWS, page=3)["rows"]) == 50
    assert cq.query_data(ROWS, page=999)["page"] == 3 and cq.query_data(ROWS, page=0)["page"] == 1


def test_source_filter_and_invalid_source():
    sponsor = cq.query_data(ROWS, source="Sponsor")
    assert sponsor["total"] == sum(1 for r in ROWS if r["source"] == "Sponsor")
    assert cq.query_data(ROWS, source="NOPE")["total"] == 250 and cq.query_data(ROWS, source="")["total"] == 250


def test_search_fields_and_cc_filter():
    assert cq.query_data(ROWS, q="GJ-17")["total"] == 11            # GJ-17, GJ-170..GJ-179
    assert cq.query_data(ROWS, q="a26-1-10-25")["total"] == 11      # new_code, case-insensitive
    assert cq.query_data(ROWS, q="memo 250")["total"] == 1          # allocation_memo
    assert cq.query_data(ROWS, cc="AAA")["total"] == 125
    assert cq.query_data(ROWS, q="no-such")["rows"] == []


def test_totals_follow_the_filter_and_never_negative_zero():
    r = cq.query_data([row(1, act=0.3, dc=300000.0), row(2, act=-0.1, dc=-100000.0), row(3, act=-0.2, dc=-200000.0)])
    assert r["sum_act"] == 0.0 and str(r["sum_act"]) == "0.0" and r["sum_dc"] == 0.0 and str(r["sum_dc"]) == "0.0"


def test_empty():
    r = cq.query_data([])
    assert r["total"] == 0 and r["pages"] == 1 and r["sum_act"] == 0.0 and r["sum_dc"] == 0.0
```

```python
# tests/test_mrc_routes.py
import io
import re

from modules.general_ledger import service as gl_service
from modules.management_report import coa_map
from modules.management_report import routes as mr_routes
from tests.test_gl_sync import mkrow
from tests.test_mrc_sources import LOG, insert_sponsor

COMBINE_HEADERS = ["Account Management", "ID#", "Date", "Allocation Memo", "Budget Activity", "COST CENTER",
                   "DEBIT - CREDIT", "Source", "COA HO", "COST CENTER2", "Month", "CC0", "CC1", "BC1",
                   "New Code", "Memo", "BC"]
APPEND1_HEADERS = ["COA", "MM", "YY", "CC", "CC.1", "Category", "Activity", "Description", "PTA", "Custom",
                   "MM.1", "ACT", "BGT"]
CMAP_ROWS = [
    {"source": "SMT", "account": "6-1810", "coa_ho": "70108100", "category": "10 - Office Supplies", "code": "-10-"},
    {"source": "ETF", "account": "6-2190", "coa_ho": "70119100", "category": "20 - Others", "code": "-20-"}]
CC_ROWS = [
    {"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16, "description": "SMT - IT"},
    {"cost_center": "POCFAD", "total_cc": "$POCFOF", "seq": 9, "description": "SMT - Finance"},
    {"cost_center": "TFOPEX", "total_cc": "$TFOPEX", "seq": 6, "description": "ETF - Opex"},
    {"cost_center": "POSPON", "total_cc": "$POCCOM", "seq": 5, "description": "SMT - Sponshorship"}]


def login(client, user="admin", password="Admin@123"):
    client.post("/auth/login", json={"username": user, "password": password})
    client.post("/select-company", data={"company_id": "2"})


def seed(client_sponsor=True, mapping=True):
    gl_service.replace_all("smt", [
        mkrow(acc_management="6-1810", tgl="2026-01-15", debit_credit=-957910.0, job_name="POITEC",
              budget_activity="SMT - IT", allocation_memo="Zoom", id_no="GJ-00168"),
        mkrow(acc_management="6-1810", tgl="2026-02-10", debit_credit=5000000.0, job_name="POCFAD",
              budget_activity="SMT - Finance", allocation_memo="ATK", id_no="GJ-00200")], LOG)
    gl_service.replace_all("etf", [
        mkrow(acc_management="6-2190", tgl="2026-02-05", debit_credit=30000.0, job_name="TFOPEX",
              budget_activity="", allocation_memo="Biaya admin", id_no="BK2-0126")], LOG)
    if client_sponsor:
        from modules.management_report import combine_sources
        insert_sponsor(combine_sources.smt_company_id(), "2026-01-19", "Prasasti Membership", 500000000.0)
    if mapping:
        coa_map.sync_coa("m.xlsb", "u", CMAP_ROWS, CC_ROWS)


def headers(html):
    return [re.sub(r"<.*?>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", html, re.S)]


def test_pages_require_login(client):
    for url in ("/management-report/gl-combine", "/management-report/append1"):
        resp = client.get(url)
        assert resp.status_code == 302 and "/auth/login" in resp.headers["Location"]


def test_gl_combine_page_shows_the_17_headers_and_all_three_sources(client):
    login(client)
    seed()
    html = client.get("/management-report/gl-combine").data.decode()
    assert headers(html) == COMBINE_HEADERS
    for text in ("Zoom", "ATK", "Biaya admin", "Prasasti Membership", "Sponsor", "$POCCOM", "A26-51"):
        assert text in html, text
    assert "-957.910" in html                                    # DEBIT - CREDIT in full rupiah
    assert "19/01/2026" in html                                  # dd/mm/yyyy


def test_append1_page_shows_the_13_headers_and_workbook_values(client):
    login(client)
    seed()
    html = client.get("/management-report/append1").data.decode()
    assert headers(html) == APPEND1_HEADERS
    assert "701078002" in html and "POSPON" in html and "500,0" in html
    assert "- Act 2026 : Prasasti Membership Month : 1" in html


def test_new_code_numbering_ignores_source_cutoff_and_search(client):
    login(client)
    seed()
    full = client.get("/management-report/gl-combine").data.decode()
    only_sponsor = client.get("/management-report/gl-combine?source=Sponsor&mm=2&q=Prasasti").data.decode()
    assert "A26-51" in full and "A26-51" in only_sponsor


def test_source_filter_and_invalid_source(client):
    login(client)
    seed()
    sp = client.get("/management-report/gl-combine?source=Sponsor").data.decode()
    assert "Prasasti Membership" in sp and "Zoom" not in sp and "Biaya admin" not in sp
    etf = client.get("/management-report/gl-combine?source=ETF").data.decode()
    assert "Biaya admin" in etf and "Zoom" not in etf and "Prasasti" not in etf
    bad = client.get("/management-report/gl-combine?source=NOPE")
    assert bad.status_code == 200 and "Zoom" in bad.data.decode() and "Prasasti" in bad.data.decode()


def test_cumulative_cutoff_defaults_to_latest_month(client):
    login(client)
    seed()
    jan = client.get("/management-report/gl-combine?yy=2026&mm=1").data.decode()
    assert "Zoom" in jan and "Prasasti" in jan and "ATK" not in jan and "Biaya admin" not in jan
    latest = client.get("/management-report/gl-combine").data.decode()
    assert "ATK" in latest and "Zoom" in latest                 # cumulative through the latest month


def test_invalid_parameters_fall_back_without_error(client):
    login(client)
    seed()
    for qs in ("?yy=abc&mm=99", "?yy=1999", "?mm=0", "?page=abc", "?page=-5", "?cc=NOPE", "?source=%3Cscript%3E"):
        for url in ("/management-report/gl-combine", "/management-report/append1"):
            assert client.get(url + qs).status_code == 200, (url, qs)


def test_user_input_is_html_escaped(client):
    login(client)
    seed()
    html = client.get("/management-report/gl-combine?q=%3Cscript%3Ealert(1)%3C/script%3E&cc=%3Cscript%3E").data.decode()
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_empty_states(client):
    login(client)
    seed(mapping=False)
    assert "Pemetaan COA belum ada" in client.get("/management-report/gl-combine").data.decode()


def test_no_source_data_message(client):
    login(client)
    coa_map.sync_coa("m.xlsb", "u", CMAP_ROWS, CC_ROWS)
    assert "Belum ada data sumber" in client.get("/management-report/gl-combine").data.decode()


def test_old_style_mapping_shows_one_resync_banner(client):
    login(client)
    seed(mapping=False)
    coa_map.sync_coa("m.xlsb", "u", CMAP_ROWS)                  # coa rows only, no cc rows
    html = client.get("/management-report/gl-combine").data.decode()
    assert html.count("Pemetaan perlu disync ulang") == 1 and "belum ada di sheet CC" not in html


def test_unmapped_account_and_cost_center_banners(client):
    login(client)
    seed()
    gl_service.replace_all("smt", [
        mkrow(acc_management="6-9999", tgl="2026-02-20", debit_credit=2000000.0, job_name="POXXXX",
              allocation_memo="Misterius")], LOG)
    html = client.get("/management-report/gl-combine").data.decode()
    assert "Belum dipetakan" in html and "6-9999" in html and "POXXXX" in html and "belum ada di sheet CC" in html


def test_tab_bar_links_and_old_tabs_unchanged(client):
    login(client)
    seed()
    page = client.get("/management-report/gl-combine").data.decode()
    for href in ("/management-report/gl-combine", "/management-report/append1", "/management-report/?tab=sync"):
        assert href in page, href
    index = client.get("/management-report/").data.decode()
    assert 'data-tab="tab-sync"' in index and 'data-tab="tab-report"' in index and 'data-tab="tab-ho"' in index
    links = re.findall(r'<a [^>]*href="/management-report/(?:gl-combine|append1)"[^>]*>', index)
    assert len(links) == 2 and all("mr-linktab" in l and "tab-btn" not in l for l in links)


def upload(client, name="Master.xlsb"):
    return client.post("/management-report/gl-combine/sync-mapping", data={"file": (io.BytesIO(b"x"), name)},
                       content_type="multipart/form-data")


def test_sync_mapping_success_unchanged_and_bad_uploads(client, monkeypatch):
    login(client)
    monkeypatch.setattr(mr_routes.coa_map, "read_mapping_sheets", lambda f: (CMAP_ROWS, CC_ROWS))
    j = upload(client).get_json()
    assert j["ok"] and j["changed"] and "SMT 1 akun" in j["pesan"] and "4 cost center" in j["pesan"]
    again = upload(client).get_json()
    assert again["ok"] and again["changed"] is False and "Sudah sinkron" in again["pesan"]
    assert upload(client, "a.xlsx").status_code == 400
    assert client.post("/management-report/gl-combine/sync-mapping", data={},
                       content_type="multipart/form-data").status_code == 400

    def boom(f):
        raise coa_map.CoaParseError("Sheet 'CC' tidak ditemukan di file.")
    monkeypatch.setattr(mr_routes.coa_map, "read_mapping_sheets", boom)
    r = upload(client)
    assert r.status_code == 400 and "tidak ditemukan" in r.get_json()["pesan"]
    assert len(coa_map.get_map()) == 2


def test_sync_mapping_database_error_is_json_500(client, monkeypatch):
    login(client)
    monkeypatch.setattr(mr_routes.coa_map, "read_mapping_sheets", lambda f: (CMAP_ROWS, CC_ROWS))

    def boom(*a, **k):
        raise RuntimeError("database is locked")
    monkeypatch.setattr(mr_routes.coa_map, "sync_coa", boom)
    r = upload(client)
    assert r.status_code == 500 and r.get_json()["ok"] is False and "database is locked" in r.get_json()["pesan"]


def test_non_admin_can_view_but_not_sync(client):
    import bcrypt
    import database
    pw_hash = bcrypt.hashpw(b"Req@12345", bcrypt.gensalt(4)).decode()
    conn = database.get_conn()
    conn.execute("INSERT INTO users (username, password_hash, role, must_change_pw) VALUES (?, ?, 'requester', 0)",
                 ("req1", pw_hash))
    conn.commit()
    conn.close()
    assert client.post("/auth/login", json={"username": "req1", "password": "Req@12345"}).status_code == 200
    client.post("/select-company", data={"company_id": "2"})
    seed()
    html = client.get("/management-report/gl-combine").data.decode()
    assert "mr-map-btn" not in html
    assert upload(client).status_code == 403


def test_mc_filters():
    assert mr_routes._mc_num(-957910.0) == "-957.910" and mr_routes._mc_num(None) == ""
    assert mr_routes._mc_mio(1234.56) == "1.234,6" and mr_routes._mc_mio(-1e-17) == "0,0"
    assert mr_routes._mc_date("2026-01-15") == "15/01/2026" and mr_routes._mc_date("") == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_mrc_query.py tests/test_mrc_routes.py -q -W ignore -p no:cacheprovider`
Expected: FAIL (modul `combine_query` tidak ada; route baru 404).

- [ ] **Step 3: Implementasi**

`modules/management_report/combine_query.py`:

```python
"""Management Report: filtering and paging of the GL Combine / Append1 rows (pure functions)."""

SOURCES = ("SMT", "ETF", "Sponsor")
_SEARCH_KEYS = ("description", "cc", "activity", "coa", "id_no", "new_code", "allocation_memo")


def list_ccs(rows) -> list:
    return sorted({r["cc"] for r in rows if r["cc"]})


def filter_source(rows, source) -> list:
    return [r for r in rows if r["source"] == source] if source in SOURCES else list(rows)


def query_data(rows, q=None, cc=None, source=None, page=1, per_page=100) -> dict:
    """Filter, then page. The order of `rows` (the build order) is kept: New Code runs in that order."""
    needle = (q or "").strip().lower()
    selected = [r for r in filter_source(rows, source)
                if (not cc or r["cc"] == cc)
                and (not needle or any(needle in str(r.get(k) or "").lower() for k in _SEARCH_KEYS))]
    total = len(selected)
    pages = max(1, -(-total // per_page))
    page = min(max(1, page), pages)
    return {"rows": selected[(page - 1) * per_page: page * per_page], "total": total,
            "sum_act": round(sum(r["act"] for r in selected), 6) + 0.0,
            "sum_dc": round(sum(r["debit_credit"] for r in selected), 2) + 0.0,
            "page": page, "pages": pages, "per_page": per_page}
```

`modules/management_report/routes.py` — tambahkan impor di bagian atas (di bawah impor modul yang ada):

```python
from modules.management_report import coa_map, combine_columns, combine_query, combine_rows, combine_sources
```

Tambahkan di bagian akhir file (route baru; jangan ubah route lama):

```python
# ---------- GL Combine / Append1 (built from GL SMT, GL ETF and Sponsorship; no Excel upload) ----------

def _mc_num(value) -> str:
    """1234567.0 -> '1.234.567'; None -> ''. Never '-0'."""
    if value is None:
        return ""
    return f"{round(float(value)) + 0.0:,.0f}".replace(",", ".")


def _mc_mio(value) -> str:
    """Rp Mio with 1 decimal, Indonesian style: 1234.56 -> '1.234,6'; never '-0,0'."""
    if value is None:
        return ""
    v = round(float(value), 1) + 0.0
    return f"{v:,.1f}".replace(",", "\0").replace(".", ",").replace("\0", ".")


def _mc_date(value) -> str:
    """ISO 2026-01-15 -> 15/01/2026; anything else is shown as is."""
    s = str(value or "")
    return f"{s[8:10]}/{s[5:7]}/{s[:4]}" if len(s) >= 10 and s[4] == "-" else s


bp.add_app_template_filter(_mc_num, "mc_num")
bp.add_app_template_filter(_mc_mio, "mc_mio")
bp.add_app_template_filter(_mc_date, "mc_date")


def _int_arg(name):
    try:
        return int(request.args.get(name))
    except (TypeError, ValueError):
        return None


def _page_arg() -> int:
    return _int_arg("page") or 1


def _resolve_period(opts):
    """Requested year/month if valid, otherwise the latest period that has data."""
    yy = _int_arg("yy")
    if yy not in opts["yys"]:
        yy = opts["yys"][-1] if opts["yys"] else None
    if yy is None:
        return None, None
    months = opts["months"][yy]
    mm = _int_arg("mm")
    return yy, (mm if mm in months else months[-1])


def _combine_page(table: str):
    cmap = coa_map.get_map()
    cc_map = coa_map.get_cc_map()
    built = combine_rows.build_combine_rows(
        {"SMT": combine_sources.gl_rows("smt"), "ETF": combine_sources.gl_rows("etf"),
         "Sponsor": combine_sources.sponsor_rows()}, cmap, cc_map)
    opts = combine_rows.period_options(built.rows)
    yy, mm = _resolve_period(opts)
    scoped = combine_rows.apply_cutoff(built.rows, yy, mm) if yy is not None else []
    ccs = combine_query.list_ccs(scoped)
    cc = (request.args.get("cc") or "").strip()
    if cc not in ccs:
        cc = ""                                        # stale/unknown CC behaves like "All Cost Center"
    source = request.args.get("source") if request.args.get("source") in combine_query.SOURCES else ""
    q = (request.args.get("q") or "").strip()
    data = combine_query.query_data(scoped, q=q, cc=cc or None, source=source or None, page=_page_arg())
    unmapped = combine_rows.unmapped_summary(scoped)
    last_map = coa_map.last_sync()
    # Old-style map (synced before the CC sheet / Code column existed): derived values are invalid until re-sync.
    needs_resync = bool(cmap) and (not cc_map or (last_map or {}).get("rows_cc", 0) == 0)
    unmapped_cc = [] if needs_resync else combine_rows.unmapped_cc_summary(scoped)
    try:
        can_manage = is_admin(get_jwt())
    except Exception:
        can_manage = False
    label, cols = combine_columns.TABLES[table]
    return render_template(
        "management_report/combine.html",
        active_tab=table, table=table, label=label, data_cols=cols, can_manage=can_manage,
        last_map=last_map, needs_resync=needs_resync, has_map=bool(cmap), has_rows=bool(built.rows),
        opts=opts, yy=yy, mm=mm, cc=cc, ccs=ccs, source=source, sources=combine_query.SOURCES, q=q, data=data,
        unmapped=unmapped, unmapped_cc=unmapped_cc, unmapped_rows=sum(u["rows"] for u in unmapped),
        unmapped_act=round(sum(u["act"] for u in unmapped), 6) + 0.0, skipped_date=built.skipped_date,
        active_page="management_report", use_unified_header=True,
    )


@bp.route("/gl-combine")
@jwt_html_required
def gl_combine():
    return _combine_page("combine")


@bp.route("/append1")
@jwt_html_required
def append1_page():
    return _combine_page("append1")


@bp.route("/gl-combine/sync-mapping", methods=["POST"])
@json_admin_required
def sync_mapping():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "pesan": "File belum dipilih."}), 400
    if not f.filename.lower().endswith(".xlsb"):
        return jsonify({"ok": False, "pesan": "File harus berformat .xlsb."}), 400
    try:
        rows, cc_rows = coa_map.read_mapping_sheets(io.BytesIO(f.read()))
        if not rows:
            raise coa_map.CoaParseError("Tidak ada pemetaan COA yang valid di sheet COA.")
    except coa_map.CoaParseError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    try:
        out = coa_map.sync_coa(f.filename, get_jwt().get("username", ""), rows, cc_rows)
    except Exception as e:
        return jsonify({"ok": False, "pesan": f"Sync gagal, pemetaan lama tidak berubah: {e}"}), 500
    counts = f"SMT {out['rows_smt']} akun, ETF {out['rows_etf']} akun, {out['rows_cc']} cost center"
    pesan = (f"Sudah sinkron: pemetaan tidak berubah ({counts})." if not out["changed"]
             else f"Sync pemetaan selesai: {counts}.")
    return jsonify({"ok": True, "pesan": pesan, **out})
```

`static/css/mr_combine.css`:

```css
/* Link-style tabs of the Management Report module (GL Combine / Append1 pages).
   Same look as .tab-btn but a different class, so app.js initTabs() (.tabs .tab-btn) never binds to them. */
.mr-linktab {
  display: inline-flex; align-items: center; padding: .5rem 1rem; border: none;
  background: var(--bg-muted); border-radius: 999px; font-size: .8rem; font-weight: 600;
  color: var(--text-muted); cursor: pointer; text-decoration: none; white-space: nowrap;
  font-family: inherit; transition: background .15s, color .15s, box-shadow .15s;
}
.mr-linktab.active {
  background: linear-gradient(135deg, var(--accent), var(--accent-2)); color: #fff;
  box-shadow: 0 4px 14px rgba(45,106,223,.3);
}
.mr-linktab:hover:not(.active) { background: var(--accent-surface); color: var(--accent-text); }
```

`templates/management_report/_linktabs.html` (bilah tab untuk halaman baru; semua tautan):

```html
<div class="tabs" style="margin-bottom:0">
  <a class="mr-linktab" href="{{ url_for('management_report.index') }}?tab=sync">Data Sync</a>
  <a class="mr-linktab" href="{{ url_for('management_report.index') }}?tab=report">Report</a>
  <a class="mr-linktab" href="{{ url_for('management_report.index') }}?tab=ho">HO Report</a>
  <a class="mr-linktab{{ ' active' if active_tab == 'combine' else '' }}" href="{{ url_for('management_report.gl_combine') }}">GL Combine</a>
  <a class="mr-linktab{{ ' active' if active_tab == 'append1' else '' }}" href="{{ url_for('management_report.append1_page') }}">Append1</a>
</div>
```

`templates/management_report/index.html` — dua perubahan kecil:
1. Di `{% block head %}` tambahkan baris pertama: `<link rel="stylesheet" href="{{ url_for('static', filename='css/mr_combine.css') }}">`
2. Di `{% block module_tabs %}`, tepat sebelum `</div>` penutup `div.tabs`, tambahkan:

```html
  <a class="mr-linktab" href="{{ url_for('management_report.gl_combine') }}">GL Combine</a>
  <a class="mr-linktab" href="{{ url_for('management_report.append1_page') }}">Append1</a>
```

`templates/management_report/combine.html`:

```html
{% extends "base.html" %}
{% block title %}Management Report - {{ label }}{% endblock %}

{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/mr_combine.css') }}">
<style>
.mc-table { border-collapse:collapse; width:100%; font-size:.8125rem; white-space:nowrap; }
.mc-table th, .mc-table td { padding:.3rem .5rem; border-bottom:1px solid var(--sl-200); }
.mc-table th { text-align:left; background:var(--sl-50); position:sticky; top:0; }
.mc-table .num { text-align:right; font-variant-numeric:tabular-nums; }
.mc-table td.wrap { white-space:normal; min-width:360px; }
.mc-wrap { overflow:auto; max-height:65vh; }
.mc-muted { color:var(--sl-500); font-size:.8125rem; }
.mc-cards { display:flex; gap:1rem; flex-wrap:wrap; margin:.5rem 0 1rem; }
.mc-card { padding:.6rem .9rem; border:1px solid var(--sl-200); border-radius:8px; min-width:150px; }
.mc-card b { display:block; font-size:1.05rem; font-variant-numeric:tabular-nums; }
.mc-filter { display:flex; gap:.5rem; flex-wrap:wrap; align-items:flex-end; margin-bottom:.75rem; }
.mc-filter label { display:flex; flex-direction:column; font-size:.75rem; }
.mc-pager { display:flex; align-items:center; gap:.75rem; margin:.6rem 0; }
.mc-warn { margin-bottom:.75rem; padding:.7rem .9rem; font-size:.8125rem; border:1px solid var(--danger); border-radius:8px; }
</style>
{% endblock %}

{% block module_tabs %}
{% include "management_report/_linktabs.html" %}
{% endblock %}

{% block content %}
{% set bulan = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'] %}
<div class="card" style="margin-bottom:1rem">
  <strong>Pemetaan COA &amp; CC</strong>
  <div class="mc-muted" style="margin:.25rem 0">
    {% if last_map %}Terakhir sync: {{ last_map.synced_at }} · {{ last_map.synced_by }} · {{ last_map.filename }} · SMT {{ last_map.rows_smt }} akun, ETF {{ last_map.rows_etf }} akun, {{ last_map.rows_cc or 0 }} cost center
    {% else %}Pemetaan belum pernah disync.{% endif %}
  </div>
  {% if can_manage %}
  <div style="margin:.5rem 0">
    <input type="file" id="mr-map-file" accept=".xlsb">
    <button class="btn btn-primary btn-sm" id="mr-map-btn" onclick="mrSyncMapping()">Sync pemetaan COA &amp; CC dari Excel</button>
    <span id="mr-map-msg" class="mc-muted"></span>
  </div>
  <div class="mc-muted">Pilih file <code>Management Report - MASTER.xlsb</code>; hanya sheet <b>COA</b> dan <b>CC</b> yang dibaca.</div>
  {% endif %}
</div>

{% if not has_map %}
<div class="card">Pemetaan COA belum ada. {% if can_manage %}Upload Management Report - MASTER.xlsb di atas untuk memulai.{% else %}Minta admin untuk sync pemetaan terlebih dahulu.{% endif %}</div>
{% elif not has_rows %}
<div class="card">Belum ada data sumber yang bisa ditampilkan. Sync GL SMT dan GL ETF di modul General Ledger, atau isi data di modul Sponsorship (GL: hanya akun berawalan 6 sampai 9 dengan Debit − Credit tidak nol).</div>
{% else %}

{% if needs_resync %}
<div class="mc-warn card">
  Pemetaan perlu disync ulang: sheet CC dan kolom Code belum dimuat, jadi COST CENTER2, CC1, BC1 dan New Code belum valid. {% if can_manage %}Upload Management Report - MASTER.xlsb lalu klik Sync pemetaan COA &amp; CC.{% else %}Minta admin untuk sync pemetaan.{% endif %}
</div>
{% endif %}
{% if unmapped %}
<div class="mc-warn card">
  <strong>{{ unmapped | length }} akun belum dipetakan</strong> ({{ unmapped_rows }} baris, ACT {{ unmapped_act | mc_mio }} Rp Mio) tampil di kategori "(Belum dipetakan)":
  {% for u in unmapped[:10] %}{{ u.source }} {{ u.account }} ({{ u.rows }}){% if not loop.last %}, {% endif %}{% endfor %}{% if unmapped | length > 10 %}, …{% endif %}.
  Perbarui sheet COA di Excel lalu sync ulang.
</div>
{% endif %}
{% if unmapped_cc %}
<div class="mc-warn card">
  {{ unmapped_cc | length }} cost center belum ada di sheet CC (COST CENTER2 kosong, CC1 = 0): {% for u in unmapped_cc[:10] %}{{ u.cc }} ({{ u.rows }}){% if not loop.last %}, {% endif %}{% endfor %}{% if unmapped_cc | length > 10 %}, …{% endif %}.
  Perbarui sheet CC di Excel lalu sync ulang.
</div>
{% endif %}
{% if skipped_date %}
<div class="mc-warn card">{{ skipped_date }} baris dilewati karena tanggalnya tidak valid.</div>
{% endif %}

<form class="mc-filter" method="get">
  <label>Tahun
    <select name="yy">{% for y in opts.yys %}<option value="{{ y }}"{{ ' selected' if y == yy else '' }}>{{ y }}</option>{% endfor %}</select>
  </label>
  <label>Cutoff bulan (kumulatif)
    <select name="mm">{% for m in opts.months[yy] %}<option value="{{ m }}"{{ ' selected' if m == mm else '' }}>s/d {{ bulan[m] }}</option>{% endfor %}</select>
  </label>
  <label>Cost Center
    <select name="cc"><option value="">All Cost Center</option>{% for c in ccs %}<option value="{{ c }}"{{ ' selected' if c == cc else '' }}>{{ c }}</option>{% endfor %}</select>
  </label>
  <label>Source
    <select name="source"><option value="">Semua</option>{% for s in sources %}<option value="{{ s }}"{{ ' selected' if s == source else '' }}>{{ s }}</option>{% endfor %}</select>
  </label>
  <label>Cari<input type="text" name="q" value="{{ q }}" placeholder="deskripsi / CC / COA / ID# / New Code"></label>
  <button class="btn btn-primary btn-sm" type="submit">Terapkan</button>
</form>

<div class="mc-cards">
  <div class="mc-card">Periode<b>Jan – {{ bulan[mm] }} {{ yy }}</b></div>
  <div class="mc-card">Baris<b>{{ data.total | mc_num }}</b></div>
  {% if table == 'combine' %}
  <div class="mc-card">Total DEBIT - CREDIT (Rp)<b>{{ data.sum_dc | mc_num }}</b></div>
  {% else %}
  <div class="mc-card">Total ACT (Rp Mio)<b>{{ data.sum_act | mc_mio }}</b></div>
  {% endif %}
</div>

{% macro cell(r, key, kind) -%}
{%- if kind == 'rp' %}<td class="num">{{ r[key] | mc_num }}</td>
{%- elif kind == 'mio' %}<td class="num">{{ r[key] | mc_mio }}</td>
{%- elif kind == 'date' %}<td>{{ r[key] | mc_date }}</td>
{%- elif kind == 'yy2' %}<td>{{ '%02d' % (r[key] % 100) }}</td>
{%- elif key == 'description' %}<td class="wrap">{{ r[key] }}</td>
{%- else %}<td>{{ r[key] }}</td>{% endif %}
{%- endmacro %}

<div class="mc-wrap">
<table class="mc-table">
  <thead><tr>{% for key, header, kind in data_cols %}<th{{ ' class="num"' | safe if kind in ('rp', 'mio') else '' }}>{{ header }}</th>{% endfor %}</tr></thead>
  <tbody>
  {% for r in data.rows %}
  <tr>{% for key, header, kind in data_cols %}{{ cell(r, key, kind) }}{% endfor %}</tr>
  {% else %}
  <tr><td colspan="{{ data_cols | length }}" class="mc-muted">Tidak ada baris yang cocok.</td></tr>
  {% endfor %}
  </tbody>
</table>
</div>
<div class="mc-pager">
  {% set qs = request.args.to_dict() %}{% set _ = qs.pop('page', none) %}
  {% if data.page > 1 %}<a class="btn btn-sm" href="?{{ (qs | urlencode) ~ ('&' if qs else '') }}page={{ data.page - 1 }}">&laquo; Sebelumnya</a>{% endif %}
  <span class="mc-muted">Halaman {{ data.page }} dari {{ data.pages }}</span>
  {% if data.page < data.pages %}<a class="btn btn-sm" href="?{{ (qs | urlencode) ~ ('&' if qs else '') }}page={{ data.page + 1 }}">Berikutnya &raquo;</a>{% endif %}
</div>
{% endif %}
{% endblock %}

{% block scripts %}
{% if can_manage %}
<script>
async function mrSyncMapping() {
  const f = document.getElementById('mr-map-file').files[0];
  const msg = document.getElementById('mr-map-msg');
  if (!f) { msg.textContent = 'Pilih file Management Report - MASTER.xlsb dulu.'; return; }
  const btn = document.getElementById('mr-map-btn');
  btn.disabled = true; msg.textContent = 'Menyinkronkan...';
  const fd = new FormData(); fd.append('file', f);
  try {
    const r = await fetch('/management-report/gl-combine/sync-mapping', {method: 'POST', body: fd, credentials: 'same-origin'});
    const j = await r.json();
    msg.textContent = j.pesan || (r.ok ? 'Selesai.' : 'Gagal.');
    if (j.ok && j.changed) setTimeout(() => location.reload(), 1200);
  } catch (e) { msg.textContent = 'Gagal sync: ' + e; }
  btn.disabled = false;
}
</script>
{% endif %}
{% endblock %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_mrc_query.py tests/test_mrc_routes.py tests/test_mrc_rows.py tests/test_mrc_sources.py tests/test_mrc_coa_map.py -q -W ignore -p no:cacheprovider`
Expected: PASS. Lalu bukti fitur lama utuh (tanpa mengubah tesnya): `python -m pytest tests/test_mr_*.py -q -W ignore -p no:cacheprovider` → semua PASS.

- [ ] **Step 5: Smoke test di browser lalu commit**

Jalankan server demo dengan DB sementara (jangan DB asli): set `config.DB_PATH` ke berkas temp SEBELUM mengimpor `database`/`app`, panggil `init_db()`, set `users.must_change_pw=0`, isi GL (`gl_service.replace_all`), pemetaan (`coa_map.sync_coa(..., CMAP_ROWS, CC_ROWS)` dari tes), dan beberapa baris Sponsorship (`insert_sponsor`), lalu `create_app().run(port=5051)` di background. Login dengan akun seed admin (admin / Admin@123, DB sementara), buka `/management-report/gl-combine` dan `/management-report/append1`; cek: bilah tab menampilkan kelima tab dan tab aktif ter-highlight, filter Source/Tahun/Cutoff/CC bekerja, kolom benar, lebar sempit tidak menyebabkan scroll horizontal halaman, dan `/management-report/` tetap menampilkan tab lama (Data Sync/Report/HO Report) dengan tombol yang masih bisa diklik serta dua tautan baru. Matikan server demo.

```bash
git add modules/management_report/combine_query.py modules/management_report/routes.py templates/management_report/combine.html templates/management_report/_linktabs.html templates/management_report/index.html static/css/mr_combine.css tests/test_mrc_query.py tests/test_mrc_routes.py
git commit -m "feat(mr): GL Combine and Append1 tabs built from GL SMT, GL ETF and Sponsorship

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Hapus tab MR dari modul General Ledger

**Files:**
- Delete: `modules/general_ledger/mr_report.py`, `templates/general_ledger/mr.html`, `tests/test_gl_mr_routes.py`, `tests/test_gl_mr_report.py`
- Modify: `modules/general_ledger/routes.py` (hapus route `/mr` dan `/mr/sync-coa`, helper `_int_arg`, `_resolve_period`, impor yang tak terpakai, filter `gl_mio` dan `gl_date` bila tak terpakai di `index.html`), `templates/general_ledger/_tabs.html` (hapus tautan MR)
- Modify tes: `tests/test_gl_routes.py` (tes tab MR dihapus), `tests/test_gl_mr_real_file.py` (dipindah di Task 5)
- Test: `tests/test_gl_routes.py`

**Interfaces:** `general_ledger.service.load_mr_source` tetap (dipakai `combine_sources.gl_rows`). Tidak ada antarmuka baru.

- [ ] **Step 1: Write the failing test**

Tambahkan di `tests/test_gl_routes.py`:

```python
def test_old_mr_tab_is_gone_from_the_general_ledger_module(client):
    login(client)
    for url in ("/general-ledger/mr", "/general-ledger/mr/sync-coa"):
        assert client.get(url).status_code in (404, 405)
    html = client.get("/general-ledger/smt").data.decode()
    assert "/general-ledger/mr" not in html
    for label in ("GL SMT", "GL ETF", "GL SETF"):
        assert label in html
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_gl_routes.py -q -W ignore -p no:cacheprovider -k old_mr_tab`
Expected: FAIL (route `/general-ledger/mr` masih ada).

- [ ] **Step 3: Implementasi**

```bash
git rm modules/general_ledger/mr_report.py templates/general_ledger/mr.html tests/test_gl_mr_routes.py tests/test_gl_mr_report.py
```

Edit `modules/general_ledger/routes.py`: hapus seluruh blok mulai dari `def _int_arg` sampai akhir file (route `mr_page` dan `sync_coa`), hapus impor `coa_map, mr_report, mr_rows, mr_columns` dan impor lain yang tidak lagi dipakai (jalankan `python -m pyflakes modules/general_ledger/routes.py` bila tersedia, atau `grep` tiap nama impor), hapus `_gl_mio` dan `_gl_date` bersama pendaftarannya hanya jika `grep -n "gl_mio\|gl_date" templates` tidak menemukan pemakaian di `templates/general_ledger/index.html`. `entity_page` tetap meneruskan `active_tab=entity`.

`templates/general_ledger/_tabs.html`: hapus baris `<a class="tab-btn..." ... >MR</a>` sehingga hanya tiga tab entitas.

Pindahkan tes yang masih relevan: tes `tests/test_gl_mr_real_file.py` dipindah ke `tests/test_mrc_real_file.py` di Task 5 (sementara tetap ada dan lulus karena hanya memakai modul MR).

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_gl_routes.py tests/test_gl_sync.py tests/test_gl_service.py tests/test_gl_parser.py tests/test_gl_real_file.py tests/test_gl_mr_real_file.py tests/test_mrc_routes.py tests/test_mrc_query.py tests/test_mrc_rows.py tests/test_mrc_sources.py tests/test_mrc_coa_map.py tests/test_dashboard.py tests/test_mr_routes.py -q -W ignore -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add modules/general_ledger/routes.py templates/general_ledger/_tabs.html tests/test_gl_routes.py
git commit -m "refactor(gl): remove the MR tab from the General Ledger module (moved to Management Report)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Uji dengan file asli (tiga sumber) dan verifikasi akhir

**Files:**
- Move: `tests/test_gl_mr_real_file.py` → `tests/test_mrc_real_file.py` (`git mv`), diperbarui
- Modify: `modules/management_report/combine_sources.py` (tidak diubah; hanya dipakai)
- Test: `tests/test_mrc_real_file.py`

**Interfaces:**
- Consumes: `combine_rows.build_combine_rows`, `combine_sources.sponsor_rows_from`, `coa_map.read_mapping_sheets`, `general_ledger.parser.read_gl_sheet`.

- [ ] **Step 1: Pindahkan dan perbarui tes file asli yang ada**

```bash
git mv tests/test_gl_mr_real_file.py tests/test_mrc_real_file.py
```

Pastikan impornya memakai modul MR (Task 1 & 2 sudah menggantinya) dan seluruh tes di dalamnya masih lulus: `python -m pytest tests/test_mrc_real_file.py -q -W ignore -p no:cacheprovider` → PASS (atau SKIPPED bila drive Y: tidak terjangkau).

- [ ] **Step 2: Tulis tes baris Sponsor terhadap `GL Combine`**

Baca dulu `tests/test_mrc_real_file.py` (hasil pindahan): ia sudah punya fixture modul `files` (mengembalikan `(path_gl, path_mr)` salinan temp) dan fixture `built` (SMT + ETF), serta helper `_norm` dan `_coa`. Pakai ulang helper itu. Tambahkan (impor yang belum ada: `sqlite3`, `from datetime import date, timedelta`, `from collections import Counter`, `from modules.management_report import coa_map, combine_sources`, `from modules.management_report.combine_rows import build_combine_rows`):

```python
REAL_DB = r"C:\Financehub\app\finance_hub.db"


def _real_sponsor_rows():
    """Sponsorship SMT rows from the real dev database, opened read-only (the test DB is isolated)."""
    if not os.path.exists(REAL_DB):
        pytest.skip("real finance_hub.db not reachable")
    conn = sqlite3.connect(f"file:{REAL_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        smt = conn.execute("SELECT id FROM companies WHERE code='SMT'").fetchone()["id"]
        return [dict(r) for r in conn.execute(
            "SELECT id, tanggal_form_sponsor, perihal, amount_request, coa, cc "
            "FROM sponsorship_transaksi WHERE company_id=?", (smt,))]
    finally:
        conn.close()


def _combine_sponsor_rows(mr_path):
    out = []
    with open_workbook(mr_path) as wb, wb.get_sheet("GL Combine") as sh:
        for i, row in enumerate(sh.rows()):
            v = [c.v for c in row] + [None] * 17
            if i == 0 or v[7] != "Sponsor" or v[10] is None:
                continue
            out.append({"date": (date(1899, 12, 30) + timedelta(days=int(v[2]))).isoformat(),
                        "mm": int(v[10]), "amount": float(v[6]), "memo": _norm(v[3]), "code": v[14]})
    return out


@pytest.fixture(scope="module")
def built_all(files):
    gl, mr = files
    rows, cc_rows = coa_map.read_mapping_sheets(mr)
    cmap = {(r["source"], r["account"]): (r["coa_ho"], r["category"], r["code"]) for r in rows}
    cc_map = {r["cost_center"]: {"total": r["total_cc"], "seq": r["seq"], "description": r["description"]}
              for r in cc_rows}
    source = {label: read_gl_sheet(gl, sheet).rows for label, sheet in (("SMT", "GL SMT"), ("ETF", "GL ETF"))}
    source["Sponsor"] = combine_sources.sponsor_rows_from(_real_sponsor_rows())
    return build_combine_rows(source, cmap, cc_map)


def test_sponsor_rows_match_the_gl_combine_sponsor_rows(files, built_all):
    theirs = _combine_sponsor_rows(files[1])
    ours = [r for r in built_all.rows if r["source"] == "Sponsor" and r["yy"] == 2026 and r["mm"] <= 9]
    assert theirs, "no Sponsor rows read from GL Combine"
    assert len(ours) == len(theirs)                                           # October is not in the workbook yet
    assert Counter(r["mm"] for r in ours) == Counter(t["mm"] for t in theirs)
    assert Counter((r["mm"], round(r["debit_credit"]), r["tgl"]) for r in ours) ==         Counter((t["mm"], round(t["amount"]), t["date"]) for t in theirs)
    assert {(r["account"], r["coa"], r["cc"], r["cost_center2"], r["cc1"], r["bc1"], r["category"])
            for r in ours} == {("701078002", "701078002", "POSPON", "$POCCOM", 5, "", "")}
    memo_hits = sum((Counter(_norm(r["allocation_memo"]) for r in ours) & Counter(t["memo"] for t in theirs)).values())
    assert memo_hits >= 0.95 * len(theirs)                                    # 83/85 measured; the rest are manual edits
    ours_codes = [r["new_code"] for r in ours]
    theirs_codes = [t["code"] for t in theirs]
    assert sorted(ours_codes) == sorted(theirs_codes)                         # A26-51 .. A26-5<n>, as a set
    same_position = sum(a == b for a, b in zip(ours_codes, theirs_codes)) / len(theirs_codes)
    # Measure `same_position` first and record it in the report. If it is >= 0.95 add
    # `assert same_position >= 0.95`; if the workbook orders Sponsor rows differently, keep only the
    # multiset check above and explain the measured ratio in a comment here.
```

- [ ] **Step 3: Perluas perbandingan `Append1` ke baris Sponsor**

Di tes `Append1` yang sudah ada (ia membangun `append3`: kunci `(coa, mm, cc, category, deskripsi ternormalisasi)` → himpunan ACT, dan memeriksa baris kita), ganti sumber baris kita dari fixture `built` ke `built_all` (yang memuat Sponsor). Untuk Sponsor kunci menjadi `(str(int(701078002.0)), mm, "POSPON", "", deskripsi)`: kategori Append1 `None` dinormalisasi `str(v[5] or "").strip() == ""` sehingga cocok dengan kategori kosong kita. Aturan tetap: baris yang kuncinya ada di `Append1` wajib memuat ACT kita (nol toleransi); baris yang kuncinya tidak ada (edit manual) dibatasi 1% dari seluruh baris kita. Jangan melonggarkan.

- [ ] **Step 4: Jalankan seluruh suite terkait dan lapor**

Run: `python -m pytest tests/test_gl_parser.py tests/test_gl_sync.py tests/test_gl_service.py tests/test_gl_routes.py tests/test_gl_real_file.py tests/test_mrc_coa_map.py tests/test_mrc_rows.py tests/test_mrc_sources.py tests/test_mrc_query.py tests/test_mrc_routes.py tests/test_mrc_real_file.py tests/test_dashboard.py tests/test_mr_append.py tests/test_mr_bgt_exports.py tests/test_mr_bgt_report.py tests/test_mr_exports.py tests/test_mr_formatting.py tests/test_mr_ho_report.py tests/test_mr_ho_template.py tests/test_mr_meta.py tests/test_mr_parser.py tests/test_mr_reconciliation.py tests/test_mr_report.py tests/test_mr_routes.py tests/test_mr_service.py tests/test_mr_sync.py -q -W ignore -p no:cacheprovider`
Expected: semua PASS (tes `test_mr_*.py` tidak diubah sama sekali: verifikasi dengan `git diff --stat HEAD~5 -- tests/test_mr_*.py` kosong). Laporkan angka terukur (jumlah baris Sponsor, kecocokan memo, urutan New Code).

- [ ] **Step 5: Commit**

```bash
git add tests/test_mrc_real_file.py
git commit -m "test(mr): verify GL Combine and Append1 rows (GL SMT, GL ETF, Sponsor) against the real workbook

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Verifikasi manual end-to-end (oleh pengguna setelah restart server)**

Login admin, buka Management Report. Pastikan tab lama (Data Sync, Report, HO Report) berjalan seperti biasa, termasuk upload Excel. Buka tab **GL Combine** dan **Append1**: klik "Sync pemetaan COA & CC dari Excel" (bila belum), lalu periksa Source "Sponsor" (85 baris Januari–September, ditambah baris Oktober), cutoff bulan, filter Source/Cost Center, dan bandingkan beberapa baris dengan sheet `GL Combine` dan `Append1` (New Code, COST CENTER2, ACT).
