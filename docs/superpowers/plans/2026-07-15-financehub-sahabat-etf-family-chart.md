# Sahabat ETF — Realisasi per Keluarga (Family Chart) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambah subsection "Realisasi per Keluarga" di accordion "Detail Tabel" halaman `/beasiswa/sahabat` — stacked bar chart + tabel companion yang mengelompokkan 11 siswa program Sahabat ETF ke 7 keluarga (hardcode mapping, bukan kolom DB baru), menampilkan realisasi per anggota dan total per keluarga.

**Architecture:** Fungsi service baru `get_family_summary()` reuse `get_siswa_summary()` yang sudah ada (sumber realisasi per siswa, sudah difilter years/pillars) lalu group by mapping statis `FAMILY_GROUPS`. Endpoint baru `/api/family_summary` pola identik endpoint `api_*` lain. Frontend: chart Chart.js stacked-bar baru (`setfRenderStackedBarChart`, terpisah dari `setfRenderBarChart` existing) + tabel companion, di-wire ke `setfApplyFilters()` yang sudah jadi titik re-fetch terpusat.

**Tech Stack:** Python 3.14, Flask, SQLite, pytest, vanilla JS + Jinja2, Chart.js 4.4.4 (sudah dipakai modul ini).

## Global Constraints

- Working directory semua command shell di plan ini: `C:\Financehub\app` (jalankan `pytest` dari situ).
- `FAMILY_GROUPS` di-hardcode di `modules/sahabat_etf/service.py` — **urutan code di tiap grup menentukan urutan member final** (bukan urutan alfabetis nama dari `get_siswa_summary`), karena itu grouping harus iterasi lewat `FAMILY_GROUPS` per-code, bukan lewat baris `get_siswa_summary()` langsung.
- 2 kode siswa dengan `nama` sama persis (kasus Cathabell: `1240700` + `4220003`) **wajib** ter-merge jadi 1 entri member dengan realisasi terjumlah — bukan 2 baris terpisah.
- Siswa dengan `siswa_code` yang tidak ada di `FAMILY_GROUPS` manapun -> fallback otomatis: `family_key` = kode dia sendiri, jadi "keluarga" berisi 1 orang. Tidak boleh hilang dari hasil, tidak boleh error.
- Label keluarga **dihasilkan otomatis** dari marga (kata terakhir `nama`) anggota pertama tiap grup, bukan hardcode string — marga yang muncul di >1 grup dapat suffix angka urut (`"Keluarga Widjaja 1"`, `"Keluarga Widjaja 2"`, dst); marga unik tanpa suffix (`"Keluarga Samaoen"`). Urutan penomoran mengikuti urutan definisi `FAMILY_GROUPS` (fam1..fam7), fallback di akhir.
- Filter `years`/`pillars` diteruskan apa adanya ke `get_siswa_summary()` yang sudah menangani semantiknya (budget selalu tampil, payment/realisasi yang difilter) — `get_family_summary` tidak menambah logic filter baru, murni agregasi ulang dari hasil yang sudah difilter.
- Endpoint baru wajib di balik `@jwt_html_required` + `@etf_company_required` (pola existing, reuse langsung).
- Chart baru pakai `setfCharts` object yang sudah ada (key `"chart-keluarga"`) supaya otomatis ke-destroy/redraw saat filter berubah — **jangan** ubah `setfRenderBarChart` (dipakai chart lain di halaman ini, mengubahnya bisa bikin chart lain ikut ter-stacked tanpa sengaja).
- Full spec: `docs/superpowers/specs/2026-07-15-financehub-sahabat-etf-family-chart-design.md`.

---

### Task 1: Service — `FAMILY_GROUPS`, label generator, `get_family_summary()`

**Files:**
- Modify: `modules/sahabat_etf/service.py`
- Test: `tests/test_sahabat_etf_service.py`

**Interfaces:**
- Produces: `FAMILY_GROUPS` (const), `get_family_summary(company_id: int, years: list = None, pillars: list = None) -> list[dict]` dengan shape `[{family_key, label, total_realisasi, members: [{nama, realisasi}, ...]}, ...]`. Dipakai Task 2 (route `/api/family_summary`).
- Consumes: `get_siswa_summary` (sudah ada, tidak diubah).

- [ ] **Step 1: Tulis test yang gagal**

Update baris import di `tests/test_sahabat_etf_service.py`:

Old string:
```python
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
    get_available_years, get_available_pillars, get_monthly_breakdown,
    get_pillar_breakdown, get_yearly_breakdown,
)
```

New string:
```python
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
    get_available_years, get_available_pillars, get_monthly_breakdown,
    get_pillar_breakdown, get_yearly_breakdown, get_family_summary,
)
```

Tambahkan di akhir file:

```python
FAM_SISWA = [
    ("5260002", "Effendi Widjaja"),
    ("1240700", "Cathabell Virginia Fernanda Widjaja"),
    ("4220003", "Cathabell Virginia Fernanda Widjaja"),
    ("1240706", "Jety Widjaja"),
    ("1230684", "Darrell Bright Lie"),
    ("1260001", "Budi Widjaja"),
    ("5250001", "Birgitta Jennifer Widjaja"),
    ("5260003", "Burhanuddin Widjaja"),
    ("5250002", "Richard Widjaja"),
    ("5260001", "Claudia Samaoen"),
    ("1210487", "Felicia Tarita Chandra"),
    ("5230001", "Joshua Darren Chandra"),
]


def _seed_all_family_siswa():
    for code, nama in FAM_SISWA:
        _add_siswa(code, nama)
        add_payment_batch(COMPANY_ID, code, "2026-01-15", "SETF", "ETF",
            [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
        _mark_complete(code)


def test_get_family_summary_groups_all_seven_families_with_correct_labels():
    _seed_all_family_siswa()
    families = get_family_summary(COMPANY_ID)
    assert len(families) == 7
    labels = [f["label"] for f in families]
    assert labels == [
        "Keluarga Widjaja 1", "Keluarga Widjaja 2", "Keluarga Widjaja 3", "Keluarga Widjaja 4",
        "Keluarga Samaoen", "Keluarga Chandra 1", "Keluarga Chandra 2",
    ]


def test_get_family_summary_merges_cathabell_two_codes_into_one_member():
    _seed_all_family_siswa()
    fam1 = get_family_summary(COMPANY_ID)[0]
    assert len(fam1["members"]) == 2  # Effendi + Cathabell (merged), bukan 3
    cathabell = [m for m in fam1["members"] if m["nama"].startswith("Cathabell")][0]
    assert cathabell["realisasi"] == 2000000  # 2 kode x 1jt masing-masing


def test_get_family_summary_total_realisasi_is_sum_of_members():
    _seed_all_family_siswa()
    fam1 = get_family_summary(COMPANY_ID)[0]
    assert fam1["total_realisasi"] == sum(m["realisasi"] for m in fam1["members"])
    assert fam1["total_realisasi"] == 3000000  # Effendi 1jt + Cathabell 2jt


def test_get_family_summary_fallback_for_unmapped_siswa():
    _add_siswa("9999999", "Siswa Baru Tanpa Grup")
    add_payment_batch(COMPANY_ID, "9999999", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}])
    _mark_complete("9999999")

    families = get_family_summary(COMPANY_ID)
    assert len(families) == 1
    fallback = families[0]
    assert fallback["family_key"] == "9999999"
    assert fallback["label"] == "Keluarga Grup"  # marga = kata terakhir nama ("...Tanpa Grup")
    assert fallback["members"] == [{"nama": "Siswa Baru Tanpa Grup", "realisasi": 500000.0}]


def test_get_family_summary_respects_years_filter():
    _seed_all_family_siswa()
    add_payment_batch(COMPANY_ID, "5260002", "2025-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 9000000}])
    _mark_complete("5260002")

    fam1_2026 = get_family_summary(COMPANY_ID, years=[2026])[0]
    effendi = [m for m in fam1_2026["members"] if m["nama"] == "Effendi Widjaja"][0]
    assert effendi["realisasi"] == 1000000  # payment 2025 tidak ikut


def test_get_family_summary_empty_when_no_siswa():
    assert get_family_summary(COMPANY_ID) == []
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_service.py -k family_summary -v`
Expected: FAIL — `ImportError: cannot import name 'get_family_summary'`

- [ ] **Step 3: Tambahkan `FAMILY_GROUPS` + helper label setelah `PROGRAM_NAME`**

Old string:
```python
from database import get_conn

PROGRAM_NAME = "Sahabat ETF"
```

New string:
```python
from database import get_conn

PROGRAM_NAME = "Sahabat ETF"

FAMILY_GROUPS = [
    # (family_key, [siswa_code, ...]) - urutan code menentukan urutan member & marga anggota
    # pertama yang dipakai untuk label (lihat _family_labels).
    ("fam1", ["5260002", "1240700", "4220003"]),  # Effendi Widjaja, Cathabell Virginia Fernanda Widjaja (2 kode historis)
    ("fam2", ["1240706", "1230684"]),              # Jety Widjaja, Darrell Bright Lie
    ("fam3", ["1260001", "5250001"]),               # Budi Widjaja, Birgitta Jennifer Widjaja
    ("fam4", ["5260003", "5250002"]),               # Burhanuddin Widjaja, Richard Widjaja
    ("fam5", ["5260001"]),                           # Claudia Samaoen (single)
    ("fam6", ["1210487"]),                           # Felicia Tarita Chandra (single)
    ("fam7", ["5230001"]),                           # Joshua Darren Chandra (single)
]


def _marga(nama):
    parts = (nama or "").split()
    return parts[-1] if parts else ""


def _family_labels(ordered_family_keys, first_nama_by_key):
    margas = [_marga(first_nama_by_key[k]) for k in ordered_family_keys]
    total_count = {}
    for m in margas:
        total_count[m] = total_count.get(m, 0) + 1
    running = {}
    labels = {}
    for k, m in zip(ordered_family_keys, margas):
        running[m] = running.get(m, 0) + 1
        labels[k] = f"Keluarga {m} {running[m]}" if total_count[m] > 1 else f"Keluarga {m}"
    return labels
```

- [ ] **Step 4: Tambahkan `get_family_summary` di akhir `modules/sahabat_etf/service.py`**

Old string (akhir fungsi `get_monthly_breakdown`, existing):
```python
    comparison = [
        {
            "bulan": m,
            "per_tahun": {str(y): realisasi_by_year_month.get(str(y), {}).get(m, 0.0) for y in years},
        }
        for m in range(1, 13)
    ]
    return {"chart_year": chart_year, "months": months, "comparison": comparison}
```

New string:
```python
    comparison = [
        {
            "bulan": m,
            "per_tahun": {str(y): realisasi_by_year_month.get(str(y), {}).get(m, 0.0) for y in years},
        }
        for m in range(1, 13)
    ]
    return {"chart_year": chart_year, "months": months, "comparison": comparison}


def get_family_summary(company_id: int, years: list = None, pillars: list = None) -> list:
    siswa_rows = get_siswa_summary(company_id, years, pillars)
    row_by_code = {r["siswa_code"]: r for r in siswa_rows}

    code_to_family = {}
    for family_key, codes in FAMILY_GROUPS:
        for code in codes:
            code_to_family[code] = family_key

    group_order = []
    groups = {}

    for family_key, codes in FAMILY_GROUPS:
        member_names = []
        realisasi_by_nama = {}
        for code in codes:
            row = row_by_code.get(code)
            if row is None:
                continue
            nama = row["nama"]
            if nama not in realisasi_by_nama:
                realisasi_by_nama[nama] = 0.0
                member_names.append(nama)
            realisasi_by_nama[nama] += row["realisasi_total"]
        if not member_names:
            continue
        groups[family_key] = {"order": member_names, "realisasi": realisasi_by_nama}
        group_order.append(family_key)

    # Siswa yang code-nya tidak ada di FAMILY_GROUPS manapun -> jadi keluarga sendiri.
    for row in siswa_rows:
        code = row["siswa_code"]
        if code in code_to_family:
            continue
        groups[code] = {"order": [row["nama"]], "realisasi": {row["nama"]: row["realisasi_total"]}}
        group_order.append(code)

    first_nama_by_key = {k: groups[k]["order"][0] for k in group_order}
    labels = _family_labels(group_order, first_nama_by_key)

    result = []
    for family_key in group_order:
        g = groups[family_key]
        members = [{"nama": nama, "realisasi": g["realisasi"][nama]} for nama in g["order"]]
        result.append({
            "family_key": family_key,
            "label": labels[family_key],
            "total_realisasi": sum(m["realisasi"] for m in members),
            "members": members,
        })
    return result
```

- [ ] **Step 5: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_service.py -v`
Expected: semua test lama tetap hijau + 6 test baru PASS.

- [ ] **Step 6: Commit**

```bash
git add modules/sahabat_etf/service.py tests/test_sahabat_etf_service.py
git commit -m "feat: add get_family_summary for Sahabat ETF family grouping"
```

---

### Task 2: Routes — endpoint `/api/family_summary`

**Files:**
- Modify: `modules/sahabat_etf/routes.py`
- Test: `tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Consumes: `get_family_summary` (Task 1), `_parse_filters()` (sudah ada).
- Produces: `GET /beasiswa/sahabat/api/family_summary` -> `{"families": [...]}`. Dipakai Task 4 (frontend fetch).

- [ ] **Step 1: Tulis test yang gagal**

Tambahkan ke `tests/test_sahabat_etf_routes.py`:

```python
def test_api_family_summary_returns_families_key(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "5260002", "nama": "Effendi Widjaja", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    resp = client.get("/beasiswa/sahabat/api/family_summary")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "families" in data
    assert data["families"][0]["label"] == "Keluarga Widjaja 1"


def test_api_family_summary_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/api/family_summary")
    assert resp.status_code == 403
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_routes.py -k family_summary -v`
Expected: FAIL — 404 (route belum ada)

- [ ] **Step 3: Update `modules/sahabat_etf/routes.py`**

Old string:
```python
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
    get_available_years, get_available_pillars, get_monthly_breakdown, get_latest_payments,
    get_pillar_breakdown, get_yearly_breakdown,
)
```

New string:
```python
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
    get_available_years, get_available_pillars, get_monthly_breakdown, get_latest_payments,
    get_pillar_breakdown, get_yearly_breakdown, get_family_summary,
)
```

Old string:
```python
@bp.route("/api/breakdown")
@jwt_html_required
@etf_company_required
def api_breakdown():
    years, pillars = _parse_filters()
    result = get_kategori_breakdown(_cid(), years, pillars)
    result["pillar"] = get_pillar_breakdown(_cid(), years)
    result["yearly"] = get_yearly_breakdown(_cid(), pillars)
    return jsonify(result)
```

New string:
```python
@bp.route("/api/breakdown")
@jwt_html_required
@etf_company_required
def api_breakdown():
    years, pillars = _parse_filters()
    result = get_kategori_breakdown(_cid(), years, pillars)
    result["pillar"] = get_pillar_breakdown(_cid(), years)
    result["yearly"] = get_yearly_breakdown(_cid(), pillars)
    return jsonify(result)


@bp.route("/api/family_summary")
@jwt_html_required
@etf_company_required
def api_family_summary():
    years, pillars = _parse_filters()
    return jsonify({"families": get_family_summary(_cid(), years, pillars)})
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_routes.py -v`
Expected: semua test lama tetap hijau + 2 test baru PASS.

- [ ] **Step 5: Commit**

```bash
git add modules/sahabat_etf/routes.py tests/test_sahabat_etf_routes.py
git commit -m "feat: add /api/family_summary route"
```

---

### Task 3: Template — subsection "Realisasi per Keluarga" di accordion Detail Tabel

**Files:**
- Modify: `templates/sahabat_etf/index.html`
- Test: `tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Produces: DOM ids `#chart-keluarga`, `#setf-family-table` (dan `tbody`-nya) — dikonsumsi Task 4 (JS).

- [ ] **Step 1: Tulis test yang gagal**

Tambahkan ke `tests/test_sahabat_etf_routes.py`:

```python
def test_index_renders_family_chart_section(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/")
    assert b'id="chart-keluarga"' in resp.data
    assert b'id="setf-family-table"' in resp.data
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_routes.py -k renders_family_chart -v`
Expected: FAIL — elemen belum ada di HTML.

- [ ] **Step 3: Update `templates/sahabat_etf/index.html`**

Old string:
```html
  <details class="setf-accordion" id="setf-detail-tabel">
    <summary>Detail Tabel</summary>
    <div class="setf-accordion-body">
      <div class="table-wrap">
        <h3>Rincian Budget vs Realisasi per Anggota</h3>
        <table id="setf-table">
```

New string:
```html
  <details class="setf-accordion" id="setf-detail-tabel">
    <summary>Detail Tabel</summary>
    <div class="setf-accordion-body">
      <div class="table-wrap">
        <h3>Realisasi per Keluarga</h3>
        <canvas id="chart-keluarga"></canvas>
        <div class="setf-compact-scroll">
          <table id="setf-family-table">
            <thead><tr><th>Keluarga</th><th>Nama</th><th class="num-right">Realisasi</th></tr></thead>
            <tbody><tr><td colspan="3" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
          </table>
        </div>
      </div>

      <div class="table-wrap">
        <h3>Rincian Budget vs Realisasi per Anggota</h3>
        <table id="setf-table">
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_routes.py -v`
Expected: semua test lama tetap hijau + 1 test baru PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/sahabat_etf/index.html tests/test_sahabat_etf_routes.py
git commit -m "feat: add Realisasi per Keluarga section markup to Detail Tabel accordion"
```

---

### Task 4: Frontend JS — `setfRenderStackedBarChart`, `setfRenderFamilyTable`, wiring

**Files:**
- Modify: `static/js/sahabat_etf.js`

**Interfaces:**
- Consumes: `GET /api/family_summary` (Task 2), DOM ids dari Task 3 (`#chart-keluarga`, `#setf-family-table`), `SETF_PALETTE`/`setfFmtJutaan`/`setfThemeColor`/`setfCharts` yang sudah ada.
- Produces: `setfRenderStackedBarChart(canvasId, families)`, `setfRenderFamilyTable(families)` — dipanggil dari `setfApplyFilters()`.

Tidak ada automated test untuk file ini (tidak ada JS test harness di proyek ini) — verifikasi lewat browser di Task 6.

- [ ] **Step 1: Tambahkan `setfRenderStackedBarChart` setelah `setfRenderBarChart`**

Old string:
```javascript
      },
    },
  });
}

let setfActiveKategoriDrilldown = null;
```

New string:
```javascript
      },
    },
  });
}

function setfRenderStackedBarChart(canvasId, families) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();

  const maxMembers = families.reduce(function (max, f) { return Math.max(max, f.members.length); }, 0);
  const datasets = [];
  for (let i = 0; i < maxMembers; i++) {
    datasets.push({
      label: "Anggota " + (i + 1),
      data: families.map(function (f) { return f.members[i] ? f.members[i].realisasi : 0; }),
      backgroundColor: SETF_PALETTE[i % SETF_PALETTE.length],
    });
  }

  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: families.map(function (f) { return f.label; }), datasets: datasets },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (item) {
              const member = families[item.dataIndex].members[item.datasetIndex];
              return member ? member.nama + ": " + setfFmtJutaan(member.realisasi) : "";
            },
          },
        },
      },
      scales: {
        x: { stacked: true, ticks: { color: setfThemeColor("--text-secondary", "#94a3b8") }, grid: { color: "rgba(148,163,184,0.1)" } },
        y: {
          stacked: true,
          ticks: {
            color: setfThemeColor("--text-secondary", "#94a3b8"),
            callback: function (value) { return setfFmtJutaan(value); },
          },
          grid: { color: "rgba(148,163,184,0.1)" },
        },
      },
    },
  });
}

let setfActiveKategoriDrilldown = null;
```

- [ ] **Step 2: Tambahkan `setfRenderFamilyTable` setelah `setfRenderTable`**

Old string:
```javascript
function setfRenderKategoriTable(kategoriRows) {
```

New string:
```javascript
function setfRenderFamilyTable(families) {
  const tbody = document.querySelector("#setf-family-table tbody");
  if (!families.length) {
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted)">Belum ada data keluarga.</td></tr>';
    return;
  }
  tbody.innerHTML = families.map(function (f) {
    const memberRows = f.members.map(function (m) {
      return "<tr><td>" + f.label + "</td><td>" + m.nama + '</td><td class="num-right">' +
        setfFmtJutaan(m.realisasi) + "</td></tr>";
    }).join("");
    return memberRows + '<tr class="setf-family-total-row"><td>' + f.label +
      ' — Total</td><td></td><td class="num-right">' + setfFmtJutaan(f.total_realisasi) + "</td></tr>";
  }).join("");
}

function setfRenderKategoriTable(kategoriRows) {
```

- [ ] **Step 3: Wiring — skeleton + fetch di `setfApplyFilters()`**

Old string:
```javascript
  setfRenderSummarySkeleton();
  document.querySelector("#setf-table tbody").innerHTML = skeletonRows(8, 6);
  document.querySelector("#setf-kategori-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-latest-payments-table tbody").innerHTML = skeletonRows(4, 6);
  document.querySelector("#setf-pillar-table tbody").innerHTML = skeletonRows(4, 4);

  setfRefetchLatestPayments();

  fetch("/beasiswa/sahabat/api/summary" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfRenderSummaryCards(data.rows);
      setfRenderTable(data.rows);
    })
    .catch(function () { showToast("Gagal memuat ringkasan anggota.", "error"); });

  fetch("/beasiswa/sahabat/api/breakdown" + (qs ? "?" + qs : ""))
```

New string:
```javascript
  setfRenderSummarySkeleton();
  document.querySelector("#setf-table tbody").innerHTML = skeletonRows(8, 6);
  document.querySelector("#setf-kategori-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-latest-payments-table tbody").innerHTML = skeletonRows(4, 6);
  document.querySelector("#setf-pillar-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-family-table tbody").innerHTML = skeletonRows(4, 3);

  setfRefetchLatestPayments();

  fetch("/beasiswa/sahabat/api/summary" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfRenderSummaryCards(data.rows);
      setfRenderTable(data.rows);
    })
    .catch(function () { showToast("Gagal memuat ringkasan anggota.", "error"); });

  fetch("/beasiswa/sahabat/api/family_summary" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfRenderStackedBarChart("chart-keluarga", data.families);
      setfRenderFamilyTable(data.families);
    })
    .catch(function () { showToast("Gagal memuat data keluarga.", "error"); });

  fetch("/beasiswa/sahabat/api/breakdown" + (qs ? "?" + qs : ""))
```

- [ ] **Step 4: Ikutkan `chart-keluarga` ke listener `fh-theme-changed`**

Old string:
```javascript
window.addEventListener("fh-theme-changed", function () {
  if (setfCharts["chart-kategori"] || setfCharts["chart-bulanan"] || setfCharts["chart-tahunan"]) {
    setfApplyFilters();
  }
});
```

New string:
```javascript
window.addEventListener("fh-theme-changed", function () {
  if (setfCharts["chart-kategori"] || setfCharts["chart-bulanan"] || setfCharts["chart-tahunan"] || setfCharts["chart-keluarga"]) {
    setfApplyFilters();
  }
});
```

- [ ] **Step 5: Commit**

```bash
git add static/js/sahabat_etf.js
git commit -m "feat: render stacked bar chart + table for Realisasi per Keluarga"
```

---

### Task 5: CSS — height cap chart + total row styling

**Files:**
- Modify: `static/css/budget.css`

**Interfaces:** tidak ada — styling saja.

- [ ] **Step 1: Tambahkan rule setelah blok `.setf-compact-card table th/td`**

Old string:
```css
.setf-compact-card table th,
.setf-compact-card table td {
  padding: 0.35rem 0.6rem;
  font-size: 0.8rem;
}
```

New string:
```css
.setf-compact-card table th,
.setf-compact-card table td {
  padding: 0.35rem 0.6rem;
  font-size: 0.8rem;
}

/* Realisasi per Keluarga (Detail Tabel): chart-nya hidup di .table-wrap polos,
   bukan .budget-chart-card, jadi butuh height cap sendiri. */
#chart-keluarga {
  max-height: 280px;
}
.setf-family-total-row td {
  font-weight: 600;
  border-top: 1px solid var(--border-color);
}
```

- [ ] **Step 2: Commit**

```bash
git add static/css/budget.css
git commit -m "style: cap chart-keluarga height, bold family total row"
```

---

### Task 6: Regression check — full test suite + manual browser verification

**Files:** (tidak ada file baru — verifikasi saja)

- [ ] **Step 1: Jalankan seluruh test suite modul**

Run: `pytest tests/test_sahabat_etf_service.py tests/test_sahabat_etf_routes.py -v`
Expected: semua test (lama + baru dari Task 1-3) hijau.

- [ ] **Step 2: Manual verification di browser**

Jalankan dev server, login, pilih company ETF, buka `/beasiswa/sahabat`, expand accordion "Detail Tabel", cek:
- Section "Realisasi per Keluarga" muncul di atas tabel "Rincian Budget vs Realisasi per Anggota".
- Stacked bar menampilkan 7 keluarga, label sesuai penomoran marga.
- Hover bar keluarga Widjaja 1 -> tooltip tampilkan nama asli (Effendi Widjaja / Cathabell...), bukan "Anggota 1/2".
- Tabel companion: baris per anggota + baris bold "Keluarga X — Total" per keluarga.
- Ganti filter Tahun/Pillar -> chart & tabel keluarga ikut ter-update.
- Toggle dark/light mode -> chart ikut redraw tanpa error di console.
- Login sebagai company non-ETF -> section ini tidak error (halaman tampilkan notice "Ganti Company" seperti biasa, endpoint API balikan 403 kalau diakses langsung).

- [ ] **Step 3: Kalau semua hijau + verifikasi manual OK, plan selesai**

---

## Ringkasan File Baru/Modifikasi

| File | Aksi |
|---|---|
| `modules/sahabat_etf/service.py` | Modify (FAMILY_GROUPS + label helper + `get_family_summary` baru) |
| `modules/sahabat_etf/routes.py` | Modify (1 route baru: `/api/family_summary`) |
| `templates/sahabat_etf/index.html` | Modify (subsection baru di accordion Detail Tabel) |
| `static/js/sahabat_etf.js` | Modify (2 fungsi baru + wiring `setfApplyFilters` + listener theme-changed) |
| `static/css/budget.css` | Modify (height cap chart + total row style) |
| `tests/test_sahabat_etf_service.py` | Modify (6 test baru) |
| `tests/test_sahabat_etf_routes.py` | Modify (3 test baru) |
