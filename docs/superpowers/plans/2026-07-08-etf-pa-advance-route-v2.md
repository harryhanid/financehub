# ETF PA Route GL vs Advance — v2 Implementation Plan (koreksi alur)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pindahkan titik keputusan Route (GL/Advance) dari "saat PA ditarik ke PAM" (v1, salah)
ke "saat PA dibuat" (v2, benar), pindahkan UI Route selector + tab Advance dari modul Payment
Memo ke modul ETF Payment Application, dan perluas `realize_advance_payment` supaya ikut
menutup PA header + baris PA saat realisasi.

**Architecture:** PA header (`etf_pa`/`app_pa`/`sml_pa`/`setf_pa`) dapat kolom `route` baru
sebagai sumber kebenaran. `create_pa()` men-stamp route ke header + semua baris saat dibuat.
`save_pa_payment` (Payment Memo) tidak lagi menerima `route` dari request — men-derive dari
PA header yang ditarik, dan menolak kalau baris yang dipilih campur route. Backend
`set_pam_complete_cascade`/`get_advance_payments`/route `/payment-memo/advance/*` (v1, sudah
benar) dipakai ulang apa adanya; `realize_advance_payment` diperluas untuk juga menutup PA
header.

**Tech Stack:** Python 3.14, Flask, SQLite (WAL mode), pytest, vanilla JS/Jinja2 templates.

## Global Constraints

- Route default selalu `"gl"` — setiap caller lama yang tidak kirim route harus tetap
  berperilaku identik dengan sebelum plan ini (regresi wajib hijau di setiap task).
- `payment_beasiswa.pillar` tetap pillar tujuan asli (AGRI/APP/LAND/SETF), tidak pernah
  `"ADVANCE"`. Yang jadi `"ADVANCE"` hanya `pam_records.pillar` (tidak berubah dari v1).
- 1 PA header = 1 route, seumur hidup PA itu (tidak berubah setelah dibuat).
- 1 PAM = 1 route — kalau baris yang ditarik ke satu PAM campur PA route gl+advance, request
  ditolak.
- Full spec: `docs/superpowers/specs/2026-07-08-etf-pa-advance-route-v2-design.md`.
- Working directory semua command shell di plan ini: `C:\Financehub\app` (jalankan `pytest`
  dari situ, bukan dari `C:\Financehub`).

---

### Task 1: Schema — kolom `route` di PA header (`etf_pa`, `app_pa`, `sml_pa`, `setf_pa`)

**Files:**
- Modify: `database.py` (`migrate_db()`, sisipkan setelah blok migrasi
  `payment_beasiswa.tgl_realisasi` yang sudah ada — baris 1059-1063, sebelum komentar
  `# rekam_medis table`)
- Test: `tests/test_advance_route_schema.py` (append)

**Interfaces:**
- Consumes: tidak ada.
- Produces: kolom `etf_pa.route`, `app_pa.route`, `sml_pa.route`, `setf_pa.route` — semua
  `TEXT DEFAULT 'gl'`, nullable-safe (ALTER TABLE ADD COLUMN dengan DEFAULT langsung mengisi
  baris lama).

- [ ] **Step 1: Write the failing test**

Tambahkan di akhir `tests/test_advance_route_schema.py`:

```python
@pytest.mark.parametrize("table", ["etf_pa", "app_pa", "sml_pa", "setf_pa"])
def test_pa_header_has_route_column(table):
    conn = get_conn()
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    conn.close()
    assert "route" in cols, f"{table} missing 'route' column"


def test_pa_header_route_defaults_to_gl():
    conn = get_conn()
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, status, created_at) VALUES (2,'PA/TEST/999/2026','open','2026-07-08T00:00:00')"
    )
    conn.commit()
    row = conn.execute(
        "SELECT route FROM etf_pa WHERE pa_number='PA/TEST/999/2026'"
    ).fetchone()
    conn.close()
    assert row["route"] == "gl"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_advance_route_schema.py -v -k pa_header`
Expected: FAIL — `assert "route" in cols` (kolom belum ada di 4 tabel header).

- [ ] **Step 3: Add the migration**

Di `database.py`, dalam `migrate_db()`, sisipkan tepat setelah blok ini (baris ~1059-1063):

```python
    try:
        conn.execute("ALTER TABLE payment_beasiswa ADD COLUMN tgl_realisasi TEXT")
        conn.commit()
    except Exception:
        pass
```

tambahkan:

```python

    # ── route pada PA header — sumber kebenaran GL/Advance (2026-07-08) ────
    for pa_hdr_tbl in ["etf_pa", "app_pa", "sml_pa", "setf_pa"]:
        try:
            conn.execute(f"ALTER TABLE {pa_hdr_tbl} ADD COLUMN route TEXT DEFAULT 'gl'")
            conn.commit()
        except Exception:
            pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_advance_route_schema.py -v`
Expected: semua test di file ini PASS (termasuk yang lama dari v1, regresi hijau).

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add app/database.py app/tests/test_advance_route_schema.py
git commit -m "feat: add route column to PA header tables (etf_pa/app_pa/sml_pa/setf_pa)"
```

---

### Task 2: `create_pa()` terima param `route`, stamp ke header + semua baris

**Files:**
- Modify: `modules/etf_payment_application/service.py` (`create_pa`, baris 346-395)
- Test: `tests/test_etf_pa_service.py` (append)

**Interfaces:**
- Consumes: kolom `route` dari Task 1.
- Produces: `create_pa(company_id, header, lines, tab="agri", route="gl")` — param baru,
  default `"gl"` (regresi aman). Header PA dan **setiap** baris yang di-insert dapat
  `route=route` yang sama.

- [ ] **Step 1: Write the failing test**

Tambahkan di akhir `tests/test_etf_pa_service.py`:

```python
def test_create_pa_route_advance_stamps_header_and_lines():
    sid = _student_id("1230001")
    result = create_pa(COMPANY_ID, {
        "tgl_payment_application": "2026-07-08",
    }, [
        {"student_id": sid, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 3", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000}
    ], route="advance")
    assert result["ok"] is True

    conn = get_conn()
    header = conn.execute(
        "SELECT route FROM etf_pa WHERE id=?", (result["pa_id"],)
    ).fetchone()
    line = conn.execute(
        "SELECT route FROM etf_pa_lines WHERE pa_id=?", (result["pa_id"],)
    ).fetchone()
    conn.close()
    assert header["route"] == "advance"
    assert line["route"]   == "advance"


def test_create_pa_default_route_is_gl():
    sid = _student_id("1230001")
    result = create_pa(COMPANY_ID, {
        "tgl_payment_application": "2026-07-08",
    }, [
        {"student_id": sid, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 3", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 1000000}
    ])
    assert result["ok"] is True
    conn = get_conn()
    header = conn.execute(
        "SELECT route FROM etf_pa WHERE id=?", (result["pa_id"],)
    ).fetchone()
    conn.close()
    assert header["route"] == "gl"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_etf_pa_service.py -k route -v`
Expected: FAIL — `TypeError: create_pa() got an unexpected keyword argument 'route'`.

- [ ] **Step 3: Implement**

Di `modules/etf_payment_application/service.py`, ubah signature `create_pa` (baris 346):

```python
def create_pa(company_id: int, header: dict, lines: list, tab: str = "agri",
              route: str = "gl") -> dict:
```

Ubah INSERT header (baris ~366-378) — tambahkan kolom `route`:

```python
    pa_number = _gen_pa_number(company_id, conn, pa_tbl, pa_prefix)
    ts = _ts()
    cur = conn.execute(
        f"""INSERT INTO {pa_tbl}
            (company_id, pa_number, tgl_payment_application, tgl_surat_pengajuan,
             keterangan, doc_received_by_educ, received_pa_from_educ, status, route, created_at)
            VALUES (?,?,?,?,?,?,?,'open',?,?)""",
        (company_id, pa_number,
         header.get("tgl_payment_application", ""),
         header.get("tgl_surat_pengajuan", ""),
         header.get("keterangan", ""),
         header.get("doc_received_by_educ", ""),
         header.get("received_pa_from_educ", ""),
         route,
         ts)
    )
    pa_id = cur.lastrowid
```

Ubah INSERT baris (baris ~380-393) — tambahkan kolom `route` ke tiap line:

```python
    for line in lines:
        conn.execute(
            f"""INSERT INTO {lines_tbl}
                (pa_id, student_id, jenis_pembayaran, semester,
                 tahun_ajaran, ipk_sem_sebelumnya, jumlah_pembayaran, route)
                VALUES (?,?,?,?,?,?,?,?)""",
            (pa_id,
             line.get("student_id"),
             line.get("jenis_pembayaran", ""),
             line.get("semester", ""),
             line.get("tahun_ajaran", ""),
             line.get("ipk_sem_sebelumnya") or 0,
             line.get("jumlah_pembayaran") or 0,
             route)
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_etf_pa_service.py -v`
Expected: semua test PASS, termasuk seluruh test lama di file ini (regresi `route="gl"` default
tidak mengubah perilaku existing).

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add app/modules/etf_payment_application/service.py app/tests/test_etf_pa_service.py
git commit -m "feat: create_pa accepts route param, stamps header + all lines"
```

---

### Task 3: Route selector di form Input (modul ETF Payment Application) + wiring `/create`

**Files:**
- Modify: `modules/etf_payment_application/routes.py` (`create()`, baris 93-109)
- Modify: `templates/etf_payment_application/index.html` (form Input baris ~332-343;
  `submitPA()` baris 1305-1340)

**Interfaces:**
- Consumes: `create_pa(..., route=...)` dari Task 2.
- Produces: tidak ada interface baru untuk task lain — ini titik akhir alur create-PA-dengan-route.

- [ ] **Step 1: Update route handler**

Di `modules/etf_payment_application/routes.py`, ubah `create()` (baris 93-109):

```python
@bp.route("/create", methods=["POST"])
@jwt_html_required
def create():
    company_id = session.get("company_id")
    tab        = request.args.get("tab", "agri").lower()
    if tab not in VALID_TABS:
        tab = "agri"
    data   = request.get_json(force=True)
    header = {
        "tgl_payment_application": data.get("tgl_payment_application", ""),
        "tgl_surat_pengajuan":     data.get("tgl_surat_pengajuan", ""),
        "keterangan":              data.get("keterangan", ""),
        "doc_received_by_educ":    data.get("doc_received_by_educ", ""),
        "received_pa_from_educ":   data.get("received_pa_from_educ", ""),
    }
    lines = data.get("lines", [])
    route = (data.get("route") or "gl").lower()
    if route not in ("gl", "advance"):
        route = "gl"
    return jsonify(create_pa(company_id, header, lines, tab, route=route))
```

- [ ] **Step 2: Add Route field to the Input form**

Di `templates/etf_payment_application/index.html`, sisipkan blok baru tepat setelah blok
"Pilih Jenis PA" (setelah baris 343, sebelum komentar `{# ── Siswa + IPK ── #}` baris 345):

```html
  {# ── Route ── #}
  <div style="margin-bottom:1rem; padding:.65rem .85rem; background:var(--bg-muted); border:1px solid var(--border); border-radius:6px">
    <div style="font-size:.8rem; font-weight:700; margin-bottom:.45rem">Route *</div>
    <div style="display:flex; gap:1.25rem; flex-wrap:wrap">
      <label style="display:flex; align-items:center; gap:.35rem; font-size:.85rem; font-weight:600; cursor:pointer">
        <input type="radio" name="pa-route" value="gl" checked style="width:15px;height:15px;accent-color:#1d4ed8">
        GL
      </label>
      <label style="display:flex; align-items:center; gap:.35rem; font-size:.85rem; font-weight:600; cursor:pointer">
        <input type="radio" name="pa-route" value="advance" style="width:15px;height:15px;accent-color:#1d4ed8">
        Advance
      </label>
    </div>
  </div>
```

- [ ] **Step 3: Send route in submitPA() payload**

Di `templates/etf_payment_application/index.html`, dalam `submitPA()` (baris 1305), tambahkan
pembacaan radio Route dan sertakan di body request (ubah bagian `const resp = await
apiFetch(...)` baris 1326-1336):

```javascript
  const selectedRoute = document.querySelector('input[name="pa-route"]:checked')?.value || 'gl';
  const resp = await apiFetch(`/etf-payment-application/create?tab=${selectedTab}`, {
    method: 'POST',
    body: JSON.stringify({
      tgl_payment_application: tglApp,
      tgl_surat_pengajuan:     document.getElementById('pa-tgl-surat').value,
      keterangan:              document.getElementById('pa-keterangan').value,
      doc_received_by_educ:    document.getElementById('pa-doc-recv').value,
      received_pa_from_educ:   document.getElementById('pa-recv-pa').value,
      route:                   selectedRoute,
      lines,
    })
  });
```

(Tambahkan baris `const selectedRoute = ...` tepat sebelum `const resp = ...`, dan tambahkan
key `route: selectedRoute,` ke object JSON yang sudah ada — baris lain di dalamnya tidak
berubah.)

- [ ] **Step 4: Manual verification**

Jalankan dev server (`preview_start` config `financehub-8081` atau serupa), login, buka
**Payment Application → Input**. Pilih Jenis PA = AGRI, Route = Advance, isi 1 baris siswa,
simpan. Query manual untuk konfirmasi:
`SELECT pa_number, route FROM etf_pa ORDER BY id DESC LIMIT 1;` → `route` harus `'advance'`.
Ulangi dengan Route = GL (default) → `route` harus `'gl'`.

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add app/modules/etf_payment_application/routes.py app/templates/etf_payment_application/index.html
git commit -m "feat: Route selector on PA creation form (ETF Payment Application Input tab)"
```

---

### Task 4: `save_pa_payment` — derive route dari PA header, tolak baris campuran route

**Files:**
- Modify: `modules/payment_memo/service.py` (`save_pa_payment`, baris 765-858)
- Test: `tests/test_pam_service.py` (ubah beberapa test existing + tambah baru)
- Test: `tests/test_pam_pa_cascade.py` (`_insert_pa` helper — tambah param `route`)

**Interfaces:**
- Consumes: kolom `route` di PA header (Task 1) dan PA lines (v1, sudah ada).
- Produces: `save_pa_payment` **tidak lagi membaca `data.get("route")`** — route di-derive dari
  `{lines_tbl}.route` milik baris `etf_pa_line_id` yang ditarik. Kalau baris yang dipilih
  berasal dari campuran route gl+advance → `{"ok": False, "pesan": "..."}`. Baris tanpa
  `etf_pa_line_id` (tidak ditarik dari PA manapun) dianggap `"gl"`.

- [ ] **Step 1: Update test helper `_insert_pa` supaya bisa buat PA dengan route tertentu**

Di `tests/test_pam_pa_cascade.py`, ubah `_insert_pa` (baris 42-57) — tambah param `route`:

```python
def _insert_pa(conn, pa_tbl, lines_tbl, pa_prefix, siswa_id, status="on_process", route="gl"):
    """Insert one PA header + one line (with given route). Returns (pa_id, line_id)."""
    cur = conn.execute(
        f"INSERT INTO {pa_tbl} (company_id, pa_number, tgl_payment_application, status, route, created_at)"
        f" VALUES (?,?,?,?,?,?)",
        (COMPANY_ID, f"PA/{pa_prefix}/001/2026", "2026-06-01", status, route, _ts())
    )
    pa_id = cur.lastrowid
    cur2 = conn.execute(
        f"INSERT INTO {lines_tbl} (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran, route)"
        f" VALUES (?,?,?,?,?)",
        (pa_id, siswa_id, "By Pendidikan", 5000000, route)
    )
    line_id = cur2.lastrowid
    conn.commit()
    return pa_id, line_id
```

(Semua caller lama tidak berubah — `route` default `"gl"` sama seperti default kolom DB.)

- [ ] **Step 2: Write the failing tests**

Tambahkan di akhir `tests/test_pam_service.py`:

```python
def test_save_pa_payment_derives_route_from_pa_header_advance():
    from modules.payment_memo.service import save_pa_payment
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S011", "Test Siswa Derive")
    )
    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, status, route, created_at) VALUES (?,?,?,?,?)",
        (COMPANY_ID, "PA/TEST/010/2026", "open", "advance", "2026-07-08T00:00:00")
    )
    pa_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran, route) VALUES (?,?,?,?,?)",
        (pa_id, sid, "By Pendidikan", 4_000_000, "advance")
    )
    line_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-08",
        "pam_no": "PAM-050-ETF-07-2026", "keterangan": "derive-test",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S011", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 4_000_000, "etf_pa_line_id": line_id}],
    })
    assert result["ok"] is True

    conn = get_conn()
    pam = conn.execute(
        "SELECT pillar FROM pam_records WHERE company_id=? AND pam_no=?",
        (COMPANY_ID, "PAM-050-ETF-07-2026")
    ).fetchone()
    pb = conn.execute(
        "SELECT advance_amount FROM payment_beasiswa WHERE pam=?",
        ("PAM-050-ETF-07-2026",)
    ).fetchone()
    conn.close()
    assert pam["pillar"] == "ADVANCE"       # derived from PA header, not request body
    assert pb["advance_amount"] == 4_000_000


def test_save_pa_payment_ignores_client_supplied_route():
    """Client tries to force route='advance' via request body, but the PA lines are all
    route='gl' — the PA header must win, request body route is ignored entirely."""
    from modules.payment_memo.service import save_pa_payment
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S012", "Test Siswa Spoof")
    )
    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, status, route, created_at) VALUES (?,?,?,?,?)",
        (COMPANY_ID, "PA/TEST/011/2026", "open", "gl", "2026-07-08T00:00:00")
    )
    pa_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran, route) VALUES (?,?,?,?,?)",
        (pa_id, sid, "By Pendidikan", 1_000_000, "gl")
    )
    line_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "route": "advance",  # spoofed, must be ignored
        "tanggal": "2026-07-08",
        "pam_no": "PAM-051-ETF-07-2026", "keterangan": "spoof-test",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S012", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 1_000_000, "etf_pa_line_id": line_id}],
    })
    assert result["ok"] is True
    conn = get_conn()
    pam = conn.execute(
        "SELECT pillar FROM pam_records WHERE company_id=? AND pam_no=?",
        (COMPANY_ID, "PAM-051-ETF-07-2026")
    ).fetchone()
    conn.close()
    assert pam["pillar"] == "AGRI"   # NOT "ADVANCE" — PA header route (gl) wins


def test_save_pa_payment_rejects_mixed_route_selection():
    from modules.payment_memo.service import save_pa_payment
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S013", "Test Siswa Mixed")
    )
    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, status, route, created_at) VALUES (?,?,?,?,?)",
        (COMPANY_ID, "PA/TEST/012/2026", "open", "gl", "2026-07-08T00:00:00")
    )
    pa_gl_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran, route) VALUES (?,?,?,?,?)",
        (pa_gl_id, sid, "By Pendidikan", 1_000_000, "gl")
    )
    line_gl_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, status, route, created_at) VALUES (?,?,?,?,?)",
        (COMPANY_ID, "PA/TEST/013/2026", "open", "advance", "2026-07-08T00:00:00")
    )
    pa_adv_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran, route) VALUES (?,?,?,?,?)",
        (pa_adv_id, sid, "By Pendidikan", 2_000_000, "advance")
    )
    line_adv_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-08",
        "pam_no": "PAM-052-ETF-07-2026", "keterangan": "mixed-test",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [
            {"siswa_code": "S013", "cat1": "By Pendidikan", "cat2": "Semester 1",
             "amount": 1_000_000, "etf_pa_line_id": line_gl_id},
            {"siswa_code": "S013", "cat1": "By Pendidikan", "cat2": "Semester 2",
             "amount": 2_000_000, "etf_pa_line_id": line_adv_id},
        ],
    })
    assert result["ok"] is False
    assert "route berbeda" in result["pesan"]

    conn = get_conn()
    pam = conn.execute(
        "SELECT id FROM pam_records WHERE company_id=? AND pam_no=?",
        (COMPANY_ID, "PAM-052-ETF-07-2026")
    ).fetchone()
    conn.close()
    assert pam is None   # nothing committed — rejected before any INSERT


def test_save_pa_payment_no_pa_line_id_defaults_to_gl():
    """Rows without etf_pa_line_id (not pulled from any PA) are treated as route='gl'."""
    from modules.payment_memo.service import save_pa_payment
    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-08",
        "pam_no": "PAM-053-ETF-07-2026", "keterangan": "no-line-id",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 500_000}],
    })
    assert result["ok"] is True
    conn = get_conn()
    pam = conn.execute(
        "SELECT pillar FROM pam_records WHERE company_id=? AND pam_no=?",
        (COMPANY_ID, "PAM-053-ETF-07-2026")
    ).fetchone()
    conn.close()
    assert pam["pillar"] == "AGRI"
```

Sekarang **ubah 3 test lama** yang tidak lagi valid (mereka pass `route: "advance"` di request
body tanpa `etf_pa_line_id` — di bawah logic baru itu akan jadi `route="gl"` dan test akan
gagal). Di `tests/test_pam_service.py`:

Hapus/ganti `test_save_pa_payment_route_advance_quarantines_pam_records` (baris 598-624) dengan:

```python
def test_save_pa_payment_route_advance_quarantines_pam_records():
    """Sekarang route berasal dari PA header, bukan request body — setup lewat PA nyata."""
    from modules.payment_memo.service import save_pa_payment
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S001", "Test Siswa 001")
    )
    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, status, route, created_at) VALUES (?,?,?,?,?)",
        (COMPANY_ID, "PA/TEST/001/2026", "open", "advance", "2026-07-07T00:00:00")
    )
    pa_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran, route) VALUES (?,?,?,?,?)",
        (pa_id, sid, "By Pendidikan", 2_000_000, "advance")
    )
    line_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab":        "agri",
        "tanggal":    "2026-07-07",
        "pam_no":     "PAM-001-ETF-07-2026",
        "keterangan": "Advance test",
        "perusahaan": "PT. ABC",
        "pillar":     "AGRI",
        "rows":       [{"siswa_code": "S001", "cat1": "By Pendidikan",
                        "cat2": "Semester 1", "amount": 2_000_000,
                        "etf_pa_line_id": line_id}],
    })
    assert result["ok"] is True
    conn = get_conn()
    pam = conn.execute(
        "SELECT pillar FROM pam_records WHERE company_id=? AND pam_no=?",
        (COMPANY_ID, "PAM-001-ETF-07-2026")
    ).fetchone()
    pb = conn.execute(
        "SELECT pillar, advance_amount FROM payment_beasiswa WHERE pam=?",
        ("PAM-001-ETF-07-2026",)
    ).fetchone()
    conn.close()
    assert pam["pillar"] == "ADVANCE"
    assert pb["pillar"]  == "AGRI"          # target pillar preserved on the line
    assert pb["advance_amount"] == 2_000_000
```

Ubah `test_get_advance_payments_returns_quarantined_lines_only` (baris 685-704) dan
`test_get_advance_payments_filters_by_status` (baris 707-717) — ganti setup pemanggilan
`save_pa_payment` yang route="advance" supaya pakai PA nyata seperti pola di atas:

```python
def test_get_advance_payments_returns_quarantined_lines_only():
    from modules.payment_memo.service import save_pa_payment, get_advance_payments
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S001", "Test Siswa 001")
    )
    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, status, route, created_at) VALUES (?,?,?,?,?)",
        (COMPANY_ID, "PA/TEST/020/2026", "open", "advance", "2026-07-07T00:00:00")
    )
    pa_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran, route) VALUES (?,?,?,?,?)",
        (pa_id, sid, "By Pendidikan", 2_500_000, "advance")
    )
    line_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-07",
        "pam_no": "PAM-020-ETF-07-2026", "keterangan": "adv",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 2_500_000, "etf_pa_line_id": line_id}],
    })
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-07",   # route=gl (default) — must NOT show up
        "pam_no": "PAM-021-ETF-07-2026", "keterangan": "gl",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 1_000_000}],
    })
    rows = get_advance_payments(COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["pam"]    == "PAM-020-ETF-07-2026"
    assert rows[0]["amount"] == 2_500_000


def test_get_advance_payments_filters_by_status():
    from modules.payment_memo.service import save_pa_payment, get_advance_payments
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S001", "Test Siswa 001")
    )
    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, status, route, created_at) VALUES (?,?,?,?,?)",
        (COMPANY_ID, "PA/TEST/022/2026", "open", "advance", "2026-07-07T00:00:00")
    )
    pa_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran, route) VALUES (?,?,?,?,?)",
        (pa_id, sid, "By Pendidikan", 1_500_000, "advance")
    )
    line_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-07",
        "pam_no": "PAM-022-ETF-07-2026", "keterangan": "adv",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 1_500_000, "etf_pa_line_id": line_id}],
    })
    assert get_advance_payments(COMPANY_ID, status="open") != []
    assert get_advance_payments(COMPANY_ID, status="paid") == []
```

`test_save_pa_payment_route_gl_default_unchanged` (baris 627-646) dan
`test_save_pa_payment_advance_tags_pa_lines_route` (baris 649-682) **tidak perlu diubah** —
yang pertama sudah tidak kirim `route` sama sekali (masih valid untuk regresi default gl), yang
kedua sudah pakai `etf_pa_line_id` dari PA nyata (masih valid), TAPI baris
`{"tab": "agri", "route": "advance", ...}` di dalamnya sekarang jadi no-op key (request body
route diabaikan) — pastikan PA line yang dibuatnya juga di-set `route='advance'` di SQL
setup-nya (baris 662-665 di file itu, `INSERT INTO etf_pa_lines (...)` — tambahkan kolom
`route` dengan value `'advance'`, karena PA header (`etf_pa`, baris 657-660) di test itu juga
perlu ditambah kolom `route='advance'`). Ubah kedua INSERT tersebut:

```python
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, status, route, created_at) VALUES (?,?,?,?,?)",
        (COMPANY_ID, "PA/TEST/001/2026", "on_process", "advance", "2026-07-07T00:00:00")
    )
    pa_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran, route) VALUES (?,?,?,?,?)",
        (pa_id, sid, "By Pendidikan", 3_000_000, "advance")
    )
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_service.py -k "derive_route or ignores_client or rejects_mixed or no_pa_line_id or advance_quarantines or get_advance_payments" -v`
Expected: FAIL — beberapa dengan `pam["pillar"] == 'AGRI'` bukan `'ADVANCE'` (route lama masih
dibaca dari request body), yang lain error karena logic tolak-campuran belum ada.

- [ ] **Step 4: Implement**

Di `modules/payment_memo/service.py`, dalam `save_pa_payment` (baris 765-858):

Hapus baris `route = (data.get("route") or "gl").lower()` (baris 783).

Ubah blok dari `pa_tbl, lines_tbl, _, _ = _TAB_CFG.get(...)` (baris 790) sampai sebelum
step "2. Create pam_records" (baris 804) jadi:

```python
    pa_tbl, lines_tbl, _, _ = _TAB_CFG.get(tab, _TAB_CFG["agri"])

    conn = get_conn()
    try:
        # 0. Derive route from the PA header of the lines being pulled — route is a
        #    decision made at create_pa() time, not here. Reject if the selected rows
        #    span PA headers with different routes.
        line_ids_for_route = [r.get("etf_pa_line_id") for r in rows if r.get("etf_pa_line_id")]
        route = "gl"
        if line_ids_for_route:
            ph0 = ",".join("?" * len(line_ids_for_route))
            route_rows = conn.execute(
                f"SELECT DISTINCT route FROM {lines_tbl} WHERE id IN ({ph0})",
                line_ids_for_route
            ).fetchall()
            distinct_routes = {(r[0] or "gl") for r in route_rows}
            if len(distinct_routes) > 1:
                conn.close()
                return {"ok": False, "pesan": "Baris yang dipilih berasal dari PA dengan route berbeda (GL dan Advance tidak bisa digabung dalam satu PAM). Pisahkan submission-nya."}
            route = distinct_routes.pop() if distinct_routes else "gl"

        # 1. Insert payment rows — does NOT create pam_record
        ins = insert_payment_rows(conn, company_id, company_code,
                                  tanggal, pillar, perusahaan, rows, route=route)
```

(Baris `if not ins.get("ok"): ...` dan seterusnya di bawahnya tidak berubah.)

Hapus baris lama step 4 yang menulis ulang route ke PA lines (baris ~846-849):

```python
            conn.execute(
                f"UPDATE {lines_tbl} SET route=? WHERE id IN ({ph})",
                [route] + list(line_ids)
            )
```

(Blok `UPDATE {pa_tbl} SET nomor_pam=?, status='on_process' ...` tepat di atasnya **tetap
ada**, hanya baris `UPDATE {lines_tbl} SET route=?` yang dihapus — route sudah final sejak
`create_pa()`, tidak boleh ditulis ulang di titik ini.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_service.py tests/test_pam_pa_cascade.py -v`
Expected: semua PASS — termasuk seluruh regresi lama di kedua file (jalur `route` tidak
dikirim / default gl tidak berubah).

- [ ] **Step 6: Commit**

```bash
cd C:\Financehub
git add app/modules/payment_memo/service.py app/tests/test_pam_service.py app/tests/test_pam_pa_cascade.py
git commit -m "fix: save_pa_payment derives route from PA header, rejects mixed-route pulls"
```

---

### Task 5: Hapus dropdown Route dari panel Input Payment Memo

**Files:**
- Modify: `templates/payment_memo/index.html` (dropdown baris 227-232; JS baris 4385, 4388)

**Interfaces:**
- Consumes: tidak ada.
- Produces: tidak ada — murni pembersihan UI, backend (Task 4) sudah tidak membaca field ini.

- [ ] **Step 1: Remove the dropdown markup**

Di `templates/payment_memo/index.html`, hapus blok ini (sekitar baris 227-232):

```html
      <div>
        <label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:2px;">Route</label>
        <select id="ipay-route" style="width:100%;padding:6px 8px;border:1px solid var(--border);border-radius:6px;">
          <option value="gl" selected>GL</option>
          <option value="advance">Advance</option>
        </select>
      </div>
```

Grid `style="display:grid;grid-template-columns:200px 140px 140px 1fr;gap:.75rem;..."` yang
membungkus blok Pillar/CC/Route/Catatan Payment (baris ~217-236) — setelah dihapus jadi 3
kolom, sesuaikan `grid-template-columns` dari `200px 140px 140px 1fr` jadi `200px 140px 1fr`.

- [ ] **Step 2: Remove the route field from the save payload**

Di JS (sekitar baris 4385-4389), ubah:

```javascript
    const route = document.getElementById('ipay-route')?.value || 'gl';
    res = await apiFetch("/payment-memo/ipay/save-pa", {
      method: "POST",
      body: JSON.stringify({ tab: type, tanggal, pam_no, keterangan, perusahaan, pillar, rows, route })
    });
```

jadi:

```javascript
    res = await apiFetch("/payment-memo/ipay/save-pa", {
      method: "POST",
      body: JSON.stringify({ tab: type, tanggal, pam_no, keterangan, perusahaan, pillar, rows })
    });
```

- [ ] **Step 3: Manual verification**

Buka **Payment Approval Memo → Input**. Pastikan field Route sudah tidak tampil, dan grid
Pillar/CC/Catatan Payment tetap rapi (3 kolom). Tarik 1 baris siswa dari PA (Task 3 sudah bisa
membuat PA advance untuk uji ini), simpan PAM — pastikan tetap berhasil (regresi Task 4 sudah
mem-verify backend-nya).

- [ ] **Step 4: Commit**

```bash
cd C:\Financehub
git add app/templates/payment_memo/index.html
git commit -m "fix: remove Route dropdown from Payment Memo Input (route now decided at PA creation)"
```

---

### Task 6: `set_pam_complete_cascade` — PA header jadi `status='paid'` untuk pillar ADVANCE

**Files:**
- Modify: `modules/payment_memo/service.py` (`set_pam_complete_cascade`, baris 2223-2307)
- Test: `tests/test_pam_pa_cascade.py` (extend test existing)

**Interfaces:**
- Consumes: tidak ada baru.
- Produces: tidak ada signature baru. Behavior: PA header (`etf_pa`/`app_pa`/`sml_pa`/
  `energy_pa`/`setf_pa`) yang di-cascade dari PAM pillar `ADVANCE` sekarang jadi
  `status='paid'` (bukan `'complete'`). PA header dari PAM non-Advance tetap `'complete'`
  seperti sebelumnya (tidak berubah).

- [ ] **Step 1: Write the failing test — extend existing test**

Di `tests/test_pam_pa_cascade.py`, ubah `test_set_pam_complete_cascade_advance_pillar_sets_paid_not_complete`
(baris 415-433) — tambahkan assertion PA header di akhir fungsi:

```python
def test_set_pam_complete_cascade_advance_pillar_sets_paid_not_complete():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pam_id, pa_id = _insert_pam_beasiswa(conn, "etf_pa", "etf_pa_lines", "ETF", "ADVANCE", sid)
    conn.close()

    result = set_pam_complete_cascade(pam_id, "2026-07-10", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pam = conn.execute("SELECT status, pillar FROM pam_records WHERE id=?", (pam_id,)).fetchone()
    pb  = conn.execute(
        "SELECT status FROM payment_beasiswa WHERE pam=?", ("PAM-ETF-06-2026-001",)
    ).fetchone()
    pa  = conn.execute("SELECT status FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()

    assert pam["status"] == "complete"   # header flow unchanged
    assert pam["pillar"] == "ADVANCE"    # not yet moved — realization hasn't happened
    assert pb["status"]  == "paid"       # NOT 'complete' — quarantined until realize
    assert pa["status"]  == "paid"       # PA header juga quarantine, bukan 'complete'
```

Tambahkan test baru untuk regresi jalur non-Advance (pastikan `_insert_pam_beasiswa` dengan
pillar biasa tetap membuat PA header `'complete'`):

```python
def test_set_pam_complete_cascade_non_advance_pillar_still_completes_pa_header():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pam_id, pa_id = _insert_pam_beasiswa(conn, "etf_pa", "etf_pa_lines", "ETF", "AGRI", sid)
    conn.close()

    result = set_pam_complete_cascade(pam_id, "2026-07-10", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pa = conn.execute("SELECT status FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert pa["status"] == "complete"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_pa_cascade.py -k "advance_pillar_sets_paid or non_advance_pillar_still_completes" -v`
Expected: FAIL pada assertion `pa["status"] == "paid"` (saat ini masih `'complete'` untuk
kedua kasus — cascade generic tidak membedakan pillar).

- [ ] **Step 3: Implement**

Di `modules/payment_memo/service.py`, dalam `set_pam_complete_cascade` (baris 2260-2303),
ubah blok `else` (source != "etf_agri") supaya PA-header cascade ikut membaca `pillar`:

```python
    else:
        pillar = pam.get("pillar") or ""
        if pillar == "ADVANCE":
            conn.execute(
                "UPDATE payment_beasiswa SET status='paid' WHERE pam=? AND company_id=?",
                (pam_no, company_id)
            )
            pa_header_status = "paid"
        else:
            paid_col = _BEASISWA_PAID_COL.get(pillar)
            if paid_col:
                conn.execute(
                    f'UPDATE payment_beasiswa SET status=\'complete\', "{paid_col}"=? '
                    f'WHERE pam=? AND company_id=?',
                    (tanggal_bayar, pam_no, company_id)
                )
            else:
                conn.execute(
                    "UPDATE payment_beasiswa SET status='complete' WHERE pam=? AND company_id=?",
                    (pam_no, company_id)
                )
            pa_header_status = "complete"
        line_ids = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT etf_pa_line_id FROM payment_beasiswa "
                "WHERE pam=? AND company_id=? AND etf_pa_line_id IS NOT NULL",
                (pam_no, company_id)
            ).fetchall()
        ]
        if line_ids:
            ph = ",".join("?" * len(line_ids))
            for lines_tbl, pa_tbl in [
                ("etf_pa_lines",    "etf_pa"),
                ("app_pa_lines",    "app_pa"),
                ("sml_pa_lines",    "sml_pa"),
                ("energy_pa_lines", "energy_pa"),
                ("setf_pa_lines",   "setf_pa"),
            ]:
                conn.execute(
                    f"""UPDATE {pa_tbl} SET tanggal_bayar=?, status=?, updated_at=?
                        WHERE id IN (
                            SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                        ) AND company_id=?""",
                    [tanggal_bayar, pa_header_status, ts] + line_ids + [company_id]
                )
```

(Perubahan: tambah variabel `pa_header_status` di kedua cabang `if pillar == "ADVANCE"` /
`else`, dan parameterisasi `status=?` di UPDATE PA-header — sebelumnya hardcoded
`status='complete'`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_pa_cascade.py -v`
Expected: semua PASS, termasuk seluruh test cascade lama (AGRI/APP/LAND/ENERGY/SETF non-Advance
tetap `'complete'`, tidak terpengaruh).

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add app/modules/payment_memo/service.py app/tests/test_pam_pa_cascade.py
git commit -m "fix: set_pam_complete_cascade sets PA header status='paid' for ADVANCE pillar"
```

---

### Task 7: `realize_advance_payment` — tutup baris PA + header PA saat realisasi

**Files:**
- Modify: `modules/payment_memo/service.py` (`realize_advance_payment`, baris 2310-2370)
- Test: `tests/test_pam_pa_cascade.py` (`_setup_paid_advance` helper — rewrite; extend/rewrite
  realize tests)

**Interfaces:**
- Consumes: `payment_beasiswa.etf_pa_line_id` (sudah ada), kolom `route`/`status` PA header
  (Task 1, Task 6).
- Produces: tidak ada signature baru — `realize_advance_payment(payment_id, realized_amount,
  tgl_realisasi, company_id)` tetap sama. Tambahan behavior: meng-update
  `{lines_tbl}.jumlah_pembayaran` baris PA jadi `realized_amount`, dan `{pa_tbl}.status` jadi
  `'complete'` begitu **semua** baris `payment_beasiswa` yang menunjuk ke baris-baris PA
  header itu sudah `'complete'`.

- [ ] **Step 1: Rewrite `_setup_paid_advance` supaya pakai PA nyata**

Di `tests/test_pam_pa_cascade.py`, ganti `_setup_paid_advance` (baris 441-459):

```python
def _setup_paid_advance(pam_no="PAM-030-ETF-07-2026", amount=3_000_000):
    """Helper: buat PA header route='advance' + 1 baris, tarik ke PAM, tandai paid.
    Returns (payment_id, pam_id, pa_id)."""
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "etf_pa", "etf_pa_lines", "ETF", sid, route="advance")
    conn.close()

    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-07",
        "pam_no": pam_no, "keterangan": "adv",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "1250001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": amount, "etf_pa_line_id": line_id}],
    })
    conn = get_conn()
    pam_id     = conn.execute(
        "SELECT id FROM pam_records WHERE company_id=? AND pam_no=?", (COMPANY_ID, pam_no)
    ).fetchone()["id"]
    payment_id = conn.execute(
        "SELECT id FROM payment_beasiswa WHERE pam=?", (pam_no,)
    ).fetchone()["id"]
    conn.close()
    set_pam_complete_cascade(pam_id, "2026-07-10", COMPANY_ID)
    return payment_id, pam_id, pa_id
```

(`"1250001"` adalah kode siswa yang selalu di-insert `_insert_siswa` — lihat baris 30-39 di
`tests/test_pam_pa_cascade.py`: `INSERT INTO siswa (..., code, ...) VALUES (..., "1250001", ...)`.
Kode ini fixed literal, sama persis setiap kali helper ini dipanggil.)

- [ ] **Step 2: Update callers of `_setup_paid_advance`**

`test_realize_advance_payment_updates_amount_and_closes_pillar` (baris 462-482) — ganti baris
`payment_id, pam_id = _setup_paid_advance()` jadi `payment_id, pam_id, pa_id =
_setup_paid_advance()`, dan tambahkan assertion PA line + header di akhir:

```python
def test_realize_advance_payment_updates_amount_and_closes_pillar():
    from modules.payment_memo.service import realize_advance_payment
    payment_id, pam_id, pa_id = _setup_paid_advance()

    result = realize_advance_payment(payment_id, 2_700_000, "2026-07-20", COMPANY_ID)
    assert result["ok"] is True
    assert result["selisih"] == 300_000   # 3_000_000 advance - 2_700_000 realized

    conn = get_conn()
    pb  = conn.execute(
        "SELECT amount, realized_amount, tgl_realisasi, status FROM payment_beasiswa WHERE id=?",
        (payment_id,)
    ).fetchone()
    pam = conn.execute("SELECT pillar FROM pam_records WHERE id=?", (pam_id,)).fetchone()
    pa  = conn.execute("SELECT status FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    line = conn.execute(
        "SELECT jumlah_pembayaran FROM etf_pa_lines WHERE pa_id=?", (pa_id,)
    ).fetchone()
    conn.close()

    assert pb["amount"]          == 2_700_000
    assert pb["realized_amount"] == 2_700_000
    assert pb["tgl_realisasi"]   == "2026-07-20"
    assert pb["status"]          == "complete"
    assert pam["pillar"]         == "AGRI"      # moved out of ADVANCE
    assert pa["status"]          == "complete"  # PA header ditutup
    assert line["jumlah_pembayaran"] == 2_700_000  # angka PA line ikut di-update
```

Update tests yang masih pakai `save_pa_payment(..., "route": "advance", ...)` langsung tanpa
`etf_pa_line_id` — `test_realize_advance_payment_rejects_not_yet_paid` (baris 485-501),
`test_realize_advance_payment_rejects_non_advance_row` (baris 504-520), dan
`test_realize_advance_payment_multi_line_partial_realization_does_not_close_pillar` (baris
523+) — ganti setup-nya pakai `_insert_pa(..., route="advance")` + `etf_pa_line_id` seperti
pola `_setup_paid_advance`:

```python
def test_realize_advance_payment_rejects_not_yet_paid():
    from modules.payment_memo.service import realize_advance_payment
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "etf_pa", "etf_pa_lines", "ETF", sid, route="advance")
    conn.close()
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-07",
        "pam_no": "PAM-031-ETF-07-2026", "keterangan": "adv",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "1250001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 1_000_000, "etf_pa_line_id": line_id}],
    })
    conn = get_conn()
    payment_id = conn.execute(
        "SELECT id FROM payment_beasiswa WHERE pam=?", ("PAM-031-ETF-07-2026",)
    ).fetchone()["id"]
    conn.close()

    result = realize_advance_payment(payment_id, 900_000, "2026-07-20", COMPANY_ID)
    assert result["ok"] is False


def test_realize_advance_payment_rejects_non_advance_row():
    from modules.payment_memo.service import realize_advance_payment
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-07",   # route=gl (no PA line pulled)
        "pam_no": "PAM-032-ETF-07-2026", "keterangan": "gl",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 1_000_000}],
    })
    conn = get_conn()
    payment_id = conn.execute(
        "SELECT id FROM payment_beasiswa WHERE pam=?", ("PAM-032-ETF-07-2026",)
    ).fetchone()["id"]
    conn.close()

    result = realize_advance_payment(payment_id, 900_000, "2026-07-20", COMPANY_ID)
    assert result["ok"] is False


def test_realize_advance_payment_multi_line_partial_realization_does_not_close_pillar():
    """Satu PA Advance dengan DUA baris siswa, ditarik jadi satu PAM. Realisasi baris
    pertama saja tidak boleh membalik pam_records.pillar dari 'ADVANCE', dan PA header
    tidak boleh 'complete' sampai KEDUA baris direalisasi."""
    from modules.payment_memo.service import realize_advance_payment

    conn = get_conn()
    sid1 = _insert_siswa(conn)
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "1250002", "Siswa Kedua")
    )
    sid2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    pa_id, _unused = _insert_pa(conn, "etf_pa", "etf_pa_lines", "ETF", sid1, route="advance")
    cur = conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran, route)"
        " VALUES (?,?,?,?,?)",
        (pa_id, sid2, "By Pendidikan", 2_000_000, "advance")
    )
    line_id_2 = cur.lastrowid
    line_id_1 = conn.execute(
        "SELECT id FROM etf_pa_lines WHERE pa_id=? AND student_id=?", (pa_id, sid1)
    ).fetchone()[0]
    conn.commit()
    conn.close()

    pam_no = "PAM-033-ETF-07-2026"
    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-07",
        "pam_no": pam_no, "keterangan": "adv-multi",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [
            {"siswa_code": "1250001", "cat1": "By Pendidikan", "cat2": "Semester 1",
             "amount": 3_000_000, "etf_pa_line_id": line_id_1},
            {"siswa_code": "1250002", "cat1": "By Pendidikan", "cat2": "Semester 1",
             "amount": 2_000_000, "etf_pa_line_id": line_id_2},
        ],
    })
    assert result["ok"] is True

    conn = get_conn()
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE company_id=? AND pam_no=?", (COMPANY_ID, pam_no)
    ).fetchone()["id"]
    payment_rows = conn.execute(
        "SELECT id, siswa_code FROM payment_beasiswa WHERE pam=? ORDER BY id", (pam_no,)
    ).fetchall()
    conn.close()

    assert len(payment_rows) == 2, "expected two payment_beasiswa rows under one pam_no"
    payment_id_1 = payment_rows[0]["id"]
    payment_id_2 = payment_rows[1]["id"]

    set_pam_complete_cascade(pam_id, "2026-07-10", COMPANY_ID)

    result1 = realize_advance_payment(payment_id_1, 2_800_000, "2026-07-20", COMPANY_ID)
    assert result1["ok"] is True

    conn = get_conn()
    pam  = conn.execute("SELECT pillar FROM pam_records WHERE id=?", (pam_id,)).fetchone()
    pa   = conn.execute("SELECT status FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert pam["pillar"] == "ADVANCE"   # belum semua baris realized
    assert pa["status"]  == "paid"      # PA header belum complete

    result2 = realize_advance_payment(payment_id_2, 1_900_000, "2026-07-21", COMPANY_ID)
    assert result2["ok"] is True

    conn = get_conn()
    pam  = conn.execute("SELECT pillar FROM pam_records WHERE id=?", (pam_id,)).fetchone()
    pa   = conn.execute("SELECT status FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert pam["pillar"] == "AGRI"      # sekarang semua baris realized
    assert pa["status"]  == "complete"  # PA header ditutup
```

(`_insert_siswa` selalu insert kode `"1250001"` — lihat baris 30-39 di
`tests/test_pam_pa_cascade.py`. Siswa kedua di-insert manual di atas dengan kode `"1250002"`,
jadi kedua literal `siswa_code` pada `rows` di atas sudah tepat, tidak perlu disesuaikan.)

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_pa_cascade.py -k realize_advance -v`
Expected: FAIL — `pa["status"]` masih `None`/error karena kolom belum diupdate,
`line["jumlah_pembayaran"]` masih nilai advance awal.

- [ ] **Step 4: Implement**

Di `modules/payment_memo/service.py`, dalam `realize_advance_payment` (baris 2310-2370), ubah
`SELECT` awal untuk ikut ambil `etf_pa_line_id` (baris 2331-2335):

```python
    conn = get_conn()
    row = conn.execute(
        "SELECT id, pam, pillar, status, advance_amount, etf_pa_line_id FROM payment_beasiswa "
        "WHERE id=? AND company_id=?",
        (payment_id, company_id)
    ).fetchone()
```

Setelah blok `remaining == 0` yang meng-update `pam_records.pillar` (baris 2358-2366),
tambahkan penutupan PA line + header sebelum `conn.commit()`:

```python
    remaining = conn.execute(
        "SELECT COUNT(*) FROM payment_beasiswa WHERE pam=? AND company_id=? AND status != 'complete'",
        (pam_no, company_id)
    ).fetchone()[0]
    if remaining == 0:
        conn.execute(
            "UPDATE pam_records SET pillar=?, updated_at=? WHERE pam_no=? AND company_id=?",
            (target_pillar, ts, pam_no, company_id)
        )

    # Update the originating PA line's amount, and close the PA header once every
    # payment_beasiswa row tracing back to that PA header is 'complete'.
    pa_line_id = row["etf_pa_line_id"]
    if pa_line_id:
        for lines_tbl, pa_tbl in [
            ("etf_pa_lines",    "etf_pa"),
            ("app_pa_lines",    "app_pa"),
            ("sml_pa_lines",    "sml_pa"),
            ("energy_pa_lines", "energy_pa"),
            ("setf_pa_lines",   "setf_pa"),
        ]:
            updated = conn.execute(
                f"UPDATE {lines_tbl} SET jumlah_pembayaran=? WHERE id=?",
                (realized_amount, pa_line_id)
            )
            if updated.rowcount:
                pa_id_row = conn.execute(
                    f"SELECT pa_id FROM {lines_tbl} WHERE id=?", (pa_line_id,)
                ).fetchone()
                pa_id = pa_id_row[0]
                sibling_line_ids = [
                    r[0] for r in conn.execute(
                        f"SELECT id FROM {lines_tbl} WHERE pa_id=?", (pa_id,)
                    ).fetchall()
                ]
                ph2 = ",".join("?" * len(sibling_line_ids))
                still_open = conn.execute(
                    f"""SELECT COUNT(*) FROM payment_beasiswa
                        WHERE etf_pa_line_id IN ({ph2}) AND status != 'complete'""",
                    sibling_line_ids
                ).fetchone()[0]
                if still_open == 0:
                    conn.execute(
                        f"UPDATE {pa_tbl} SET status='complete', updated_at=? WHERE id=?",
                        (ts, pa_id)
                    )
                break  # found the table this line belongs to, no need to try the rest

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Realisasi tersimpan.", "selisih": selisih}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_pa_cascade.py -v`
Expected: semua PASS — termasuk regresi penuh file ini (AGRI/APP/LAND/ENERGY/SETF cascade
lama, plus seluruh test Advance yang baru saja di-rewrite).

- [ ] **Step 6: Commit**

```bash
cd C:\Financehub
git add app/modules/payment_memo/service.py app/tests/test_pam_pa_cascade.py
git commit -m "feat: realize_advance_payment closes PA line + header on full realization"
```

---

### Task 8: Backend — route `/etf-payment-application/advance-data` (company-wide, lintas pillar)

**Files:**
- Modify: `modules/etf_payment_application/routes.py` (route baru, dekat `summary_data()`
  baris 191-204)

**Interfaces:**
- Consumes: `get_pa_flat` (sudah ada, tidak berubah).
- Produces: `GET /etf-payment-application/advance-data?status=` → JSON array baris PA dengan
  `route == 'advance'` dari SEMUA pillar (AGRI/APP/LAND/SETF), masing-masing di-tag
  `pillar=<tab>` — struktur sama seperti `/summary-data`.

- [ ] **Step 1: Implement**

Di `modules/etf_payment_application/routes.py`, tambahkan setelah `summary_data()` (setelah
baris 204):

```python

@bp.route("/advance-data")
@jwt_html_required
def advance_data():
    company_id = session.get("company_id")
    status     = request.args.get("status", "").strip().lower()
    all_data   = []
    for t in VALID_TABS:
        rows = get_pa_flat(company_id, tab=t)
        for r in rows:
            if (r.get("route") or "gl") != "advance":
                continue
            if status and (r.get("status") or "").lower() != status:
                continue
            r['nama_student'] = r.get('nama', '')
            r['pillar'] = t
            all_data.append(r)
    all_data.sort(key=lambda x: x.get('pa_number', ''), reverse=True)
    return jsonify(all_data)
```

- [ ] **Step 2: Manual verification**

Dengan dev server jalan, login, buat 1 PA route=advance (pakai Task 3), lalu buka di browser:
`http://127.0.0.1:<port>/etf-payment-application/advance-data` — pastikan response JSON berisi
baris PA tadi dengan `"route": "advance"` dan `"pillar": "agri"`. Coba juga dengan
`?status=open` dan `?status=complete` untuk konfirmasi filter jalan.

- [ ] **Step 3: Commit**

```bash
cd C:\Financehub
git add app/modules/etf_payment_application/routes.py
git commit -m "feat: add /etf-payment-application/advance-data route (cross-pillar Advance list)"
```

---

### Task 9: Frontend — tab "Advance" baru di modul ETF Payment Application

**Files:**
- Modify: `templates/etf_payment_application/index.html` (tab bar loop baris 230; guard
  filter-bar baris 222 & 240; blok konten baru setelah Summary tab, sebelum `{% endif %}`
  baris 721; `_tab()` di routes.py)
- Modify: `modules/etf_payment_application/routes.py` (`_tab()` baris 29-35, `index()` baris
  38-64)

**Interfaces:**
- Consumes: `/etf-payment-application/advance-data` (Task 8).
- Produces: tidak ada interface baru — task terakhir di plan ini.

- [ ] **Step 1: Recognize `tab=advance` in the route handler**

Di `modules/etf_payment_application/routes.py`, ubah `_tab()` (baris 29-35):

```python
def _tab(allow_input: bool = False, allow_summary: bool = False, allow_advance: bool = False):
    t = request.args.get("tab", "summary").lower()
    if allow_input and t == "input":
        return "input"
    if allow_summary and t == "summary":
        return "summary"
    if allow_advance and t == "advance":
        return "advance"
    return t if t in VALID_TABS else "summary"
```

Ubah `index()` (baris 38-51) — panggil dengan `allow_advance=True` dan kecualikan `"advance"`
dari cabang yang memanggil `get_pa_flat`:

```python
@bp.route("/")
@jwt_html_required
def index():
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))
    company_id = session["company_id"]
    tab = _tab(allow_input=True, allow_summary=True, allow_advance=True)
    sf = ""
    pa_rows = []
    if tab not in ("input", "summary", "advance"):
        sf = request.args.get("sf", "active").lower()
        if sf not in ("open", "on_process", "complete", "active", ""):
            sf = "active"
        pa_rows = get_pa_flat(company_id, tab, sf)
```

(Baris `return render_template(...)` di bawahnya tidak berubah.)

- [ ] **Step 2: Add "Advance" to the tab bar**

Di `templates/etf_payment_application/index.html`, ubah tab-bar loop (baris ~230):

```html
  {% for t, label in [('summary','Open PA'),('advance','Advance'),('input','Input'),('agri','AGRI'),('app','APP'),('sml','LAND'),('setf','SETF')] %}
```

Ubah kedua guard `{% if active_tab not in ('input', 'summary') %}` (baris 222 dan 240) jadi:

```html
  {% if active_tab not in ('input', 'summary', 'advance') %}
```

(Ini mencegah "Full Screen" button dan filter/bulk-bar generik AGRI/APP/LAND/SETF ikut tampil
di tab Advance — tab Advance akan punya filter bar sendiri.)

- [ ] **Step 3: Add the Advance tab content block**

Sisipkan blok baru tepat sebelum `{% endif %}{# end input/data tab conditional #}` (baris 721,
setelah blok `{% elif active_tab == 'summary' %}` yang berakhir di situ):

```html
{% elif active_tab == 'advance' %}
{# ── Advance Tab (cross-pillar) ────────────────────────────────── #}

<div style="display:flex; flex-wrap:wrap; gap:.5rem; align-items:flex-end; margin-bottom:.75rem; padding:.65rem .75rem; background:var(--bg-muted,#f8f9fa); border-radius:6px; border:1px solid var(--border)">
  <div class="form-group" style="margin:0; width:170px">
    <label style="font-size:.72rem; font-weight:600">No PA</label>
    <input type="text" id="adv-pa-number" placeholder="Cari no PA..." oninput="renderAdvance()" style="font-size:.82rem">
  </div>
  <div class="form-group" style="margin:0; width:150px">
    <label style="font-size:.72rem; font-weight:600">Status</label>
    <select id="adv-status" onchange="renderAdvance()" style="font-size:.82rem">
      <option value="">Semua</option>
      <option value="open">Open</option>
      <option value="on_process">On Process</option>
      <option value="paid">Paid (Menunggu Realisasi)</option>
      <option value="complete">Complete</option>
    </select>
  </div>
  <div class="form-group" style="margin:0; width:200px">
    <label style="font-size:.72rem; font-weight:600">Cari Nama Student</label>
    <input type="text" id="adv-nama" placeholder="Ketik nama..." oninput="renderAdvance()" style="font-size:.82rem">
  </div>
  <button class="btn btn-secondary" onclick="document.getElementById('adv-pa-number').value=''; document.getElementById('adv-status').value=''; document.getElementById('adv-nama').value=''; renderAdvance();" style="font-size:.8rem; align-self:flex-end">Reset</button>
</div>

<div style="margin-top:.25rem">
  <div id="advance-loading" style="text-align:center; padding:2rem; color:var(--text-muted)">Memuat data Advance...</div>
  <div id="advance-wrap" style="display:none; overflow-x:auto; max-height:calc(100vh - 230px); overflow-y:auto">
    <table id="advance-table" style="width:100%; border-collapse:collapse; font-size:.8rem">
      <thead>
        <tr style="background:var(--bg-muted); position:sticky; top:0; z-index:2">
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">#</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">PA Number</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Pillar</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Tgl PA</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Status</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Nama Student</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Jenis Pembayaran</th>
          <th style="padding:.5rem .6rem; text-align:right; white-space:nowrap; border-bottom:2px solid var(--border)">Jumlah (IDR)</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Nomor PAM</th>
        </tr>
      </thead>
      <tbody id="advance-tbody"></tbody>
    </table>
  </div>
  <div id="advance-count" style="margin-top:.4rem; font-size:.75rem; color:var(--text-muted)"></div>
</div>

<script>
(function() {
  let _advanceRows = [];

  const _PILLAR_STYLE = {
    agri: 'background:#fef3c7;color:#92400e;border:1px solid #d97706',
    app:  'background:#ede9fe;color:#4c1d95;border:1px solid #7c3aed',
    sml:  'background:#d1fae5;color:#064e3b;border:1px solid #059669',
    setf: 'background:#cffafe;color:#164e63;border:1px solid #0891b2',
  };
  const _PILLAR_LABEL = { agri:'AGRI', app:'APP', sml:'LAND', setf:'SETF' };
  const _STATUS_STYLE = {
    open:       'background:#dbeafe;color:#1d4ed8;border:1px solid #93c5fd',
    on_process: 'background:#fef3c7;color:#92400e;border:1px solid #fbbf24',
    paid:       'background:#ffe4e6;color:#9f1239;border:1px solid #fb7185',
    complete:   'background:#d1fae5;color:#065f46;border:1px solid #6ee7b7',
  };
  const _STATUS_LABEL = { open:'Open', on_process:'On Process', paid:'Paid', complete:'Complete' };
  const _BADGE_BASE = 'border-radius:.25rem;padding:.1rem .4rem;font-size:.7rem;font-weight:700;white-space:nowrap;display:inline-block';

  function _pillarBadge(p) {
    const s = _PILLAR_STYLE[p] || 'background:#f1f5f9;color:#475569;border:1px solid #cbd5e1';
    return `<span style="${s};${_BADGE_BASE}">${_PILLAR_LABEL[p] || (p||'').toUpperCase()}</span>`;
  }
  function _statusBadge(st) {
    const k = (st||'').toLowerCase();
    const s = _STATUS_STYLE[k] || 'background:#f1f5f9;color:#475569;border:1px solid #cbd5e1';
    return `<span style="${s};${_BADGE_BASE}">${_STATUS_LABEL[k] || st || '-'}</span>`;
  }

  window.renderAdvance = function() {
    const paNumber = (document.getElementById('adv-pa-number').value || '').toLowerCase().trim();
    const status   = (document.getElementById('adv-status').value    || '').toLowerCase().trim();
    const nama     = (document.getElementById('adv-nama').value      || '').toLowerCase().trim();

    const filtered = _advanceRows.filter(r => {
      if (paNumber && !(r.pa_number    || '').toLowerCase().includes(paNumber)) return false;
      if (status   && (r.status        || '').toLowerCase() !== status)         return false;
      if (nama     && !(r.nama_student || '').toLowerCase().includes(nama))     return false;
      return true;
    });

    const tbody = document.getElementById('advance-tbody');
    tbody.innerHTML = filtered.map((r, i) => `
      <tr style="border-bottom:1px solid var(--border)">
        <td style="padding:.4rem .6rem; color:var(--text-muted)">${i+1}</td>
        <td style="padding:.4rem .6rem; font-weight:600; white-space:nowrap">${r.pa_number || ''}</td>
        <td style="padding:.4rem .6rem">${_pillarBadge(r.pillar)}</td>
        <td style="padding:.4rem .6rem; white-space:nowrap">${r.tgl_payment_application || '-'}</td>
        <td style="padding:.4rem .6rem">${_statusBadge(r.status)}</td>
        <td style="padding:.4rem .6rem">${r.nama_student || '-'}</td>
        <td style="padding:.4rem .6rem">${r.jenis_pembayaran || '-'}</td>
        <td style="padding:.4rem .6rem; text-align:right; font-variant-numeric:tabular-nums">${(r.jumlah_pembayaran||0).toLocaleString('id-ID')}</td>
        <td style="padding:.4rem .6rem">${r.nomor_pam || '-'}</td>
      </tr>`).join('');
    document.getElementById('advance-count').textContent = `${filtered.length} PA Advance${filtered.length < _advanceRows.length ? ' (dari ' + _advanceRows.length + ')' : ''}`;
  };

  fetch('/etf-payment-application/advance-data')
    .then(r => r.json())
    .then(rows => {
      _advanceRows = rows;
      document.getElementById('advance-loading').style.display = 'none';
      document.getElementById('advance-wrap').style.display = 'block';
      renderAdvance();
    })
    .catch(err => {
      document.getElementById('advance-loading').textContent = 'Gagal memuat data: ' + err.message;
    });
})();
</script>
{% endif %}{# end input/data tab conditional #}
```

(Hapus `{% endif %}{# end input/data tab conditional #}` yang lama di baris 721 — sudah
dipindah jadi bagian dari blok di atas, jangan sampai ada 2 `{% endif %}` berturutan untuk
conditional yang sama.)

- [ ] **Step 4: Manual verification**

Jalankan dev server, buka **Payment Application**, konfirmasi urutan tab jadi
`Open PA | Advance | Input | AGRI | APP | LAND | SETF`. Klik tab **Advance** — pastikan PA
route=advance yang dibuat di Task 3 muncul dengan badge Pillar AGRI dan Status sesuai. Uji
filter status & nama. Klik tab lain (AGRI/Open PA) — pastikan tidak error dan filter/bulk bar-nya
tetap muncul seperti biasa (regresi visual).

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add app/modules/etf_payment_application/routes.py app/templates/etf_payment_application/index.html
git commit -m "feat: add Advance tab (cross-pillar) to ETF Payment Application module"
```

---

### Task 10: Verifikasi manual end-to-end (alur penuh)

**Files:** tidak ada file diubah — verifikasi murni.

Dengan dev server jalan (`preview_start` atau `python run_production.py`), login sebagai ETF,
jalankan alur penuh secara berurutan:

1. **Payment Application → Input**: buat PA baru, Jenis PA = AGRI, Route = **Advance**, isi 1
   baris siswa amount 2.000.000. Simpan.
2. **Payment Application → Advance**: konfirmasi PA tadi muncul, status **Open**, Pillar AGRI.
3. **Payment Application → Open PA / AGRI**: konfirmasi PA yang sama juga muncul di sini
   (kolom Route menampilkan "Advance" — dari v1 Task 8 yang sudah benar lokasinya).
4. **Payment Approval Memo → Input**: cari siswa tadi, pastikan baris PA-nya muncul untuk
   ditarik (dan **tidak ada** dropdown Route lagi di panel ini). Tarik baris, isi No. PAM,
   simpan.
5. **Payment Application → Advance**: refresh, konfirmasi PA tadi sekarang status
   **On Process**.
6. **Payment Approval Memo → AGRI** (atau tab pillar sesuai): cari PAM yang baru dibuat, set
   `tanggal_bayar` (tombol "set paid" yang sudah ada).
7. **Payment Application → Advance**: refresh, konfirmasi PA tadi sekarang status **Paid**.
8. **Payment Approval Memo → Advance** (`tab-pa-advance`, tab yang sudah ada dari v1): cari
   baris yang sama, klik **Realisasi**, masukkan angka realized (mis. 1.800.000) + tanggal.
9. **Payment Application → Advance**: refresh, konfirmasi PA tadi sekarang status
   **Complete**.
10. **Payment Application → AGRI**: konfirmasi baris siswa itu sekarang menampilkan jumlah
    pembayaran **1.800.000** (angka realized, bukan 2.000.000 advance awal).

Jalankan juga full regression test suite untuk memastikan tidak ada yang rusak:

```bash
cd C:\Financehub\app
python -m pytest tests/test_advance_route_schema.py tests/test_etf_pa_service.py tests/test_pam_service.py tests/test_pam_pa_cascade.py tests/test_memo_api.py -v
```

Expected: semua PASS (abaikan `PermissionError` di teardown `os.remove()` — itu Windows
SQLite WAL file-lock, bukan kegagalan test sesungguhnya, sudah dikonfirmasi di sesi
sebelumnya).

Kalau semua langkah di atas berhasil, plan ini selesai — tidak perlu commit tambahan (Task 10
murni verifikasi).
