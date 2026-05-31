# PAM Draft Memo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Draft Memo" tab to the Payment Memo page that lets users select a PAM record, preview the standard PAM form (Book6.xlsx layout), and download a PDF (2 pages) or Excel (2 sheets) export.

**Architecture:** New `exports.py` module handles PDF/ReportLab and Excel/openpyxl generation; `service.py` gains one query helper; two new routes serve the downloads; the template gains a fourth tab with a PAM-No search dropdown and JS-rendered form preview.

**Tech Stack:** Python/Flask, ReportLab 4.x, openpyxl 3.x, SQLite (existing), Jinja2

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `app/config.py` | Modify | Add `PAM_APPROVED_BY_1/2` constants |
| `app/modules/payment_memo/service.py` | Modify | Add `get_pam_payments()` |
| `app/modules/payment_memo/exports.py` | **Create** | `export_pam_pdf()`, `export_pam_excel()` |
| `app/modules/payment_memo/routes.py` | Modify | 2 new export routes + pass config to template |
| `app/templates/payment_memo/index.html` | Modify | Tab 4 "Draft Memo" (HTML + JS) |
| `app/tests/test_pam_service.py` | Modify | Tests for `get_pam_payments()` |
| `app/tests/test_pam_exports.py` | **Create** | Tests for PDF/Excel export functions |

---

## Task 1: Config defaults

**Files:**
- Modify: `app/config.py` (after line 120)
- Modify: `app/modules/payment_memo/routes.py` (index route)

- [ ] **Step 1: Add constants to config.py**

  Open `app/config.py` and add after line 120 (`PAM_DEFAULT_REQUESTOR = ...`):

  ```python
  PAM_APPROVED_BY_1 = "Hong Tjhin"
  PAM_APPROVED_BY_2 = "Tenti Kidjo"
  ```

- [ ] **Step 2: Pass constants to template in routes.py**

  In `app/modules/payment_memo/routes.py`, locate the `index()` route's `render_template()` call and add two kwargs:

  ```python
  return render_template(
      "payment_memo/index.html",
      memos=memos,
      drafts=drafts,
      cat1_list=config.CAT1_BGT,
      cat2_list=config.CAT2_SEM,
      pam_approved_by_1=config.PAM_APPROVED_BY_1,
      pam_approved_by_2=config.PAM_APPROVED_BY_2,
      active_page="payment_memo",
      **_ctx()
  )
  ```

- [ ] **Step 3: Verify no import error**

  ```bash
  cd C:/Financehub/app && python -c "import config; print(config.PAM_APPROVED_BY_1, config.PAM_APPROVED_BY_2)"
  ```

  Expected output: `Hong Tjhin Tenti Kidjo`

- [ ] **Step 4: Commit**

  ```bash
  git add app/config.py app/modules/payment_memo/routes.py
  git commit -m "feat(pam): add PAM_APPROVED_BY_1/2 config defaults"
  ```

---

## Task 2: `get_pam_payments()` service function + test

**Files:**
- Modify: `app/modules/payment_memo/service.py` (append before `export_memo_pdf`)
- Modify: `app/tests/test_pam_service.py`

- [ ] **Step 1: Write failing test**

  Open `app/tests/test_pam_service.py`. Add the import at the top and the test at the bottom:

  ```python
  # Add to imports at top of file:
  from modules.payment_memo.service import get_pam_payments

  # Add at bottom of file:
  def _seed_siswa_and_payment(conn, company_id, pam_no):
      conn.execute(
          """INSERT INTO siswa (company_id, code, nama, bank, norek, namarek,
             jenjang, program, status)
             VALUES (?,?,?,?,?,?,?,?,?)""",
          (company_id, "S001", "Harry Santoso", "BCA", "1234567890",
           "Harry Santoso", "S1", "SMART", "Aktif")
      )
      conn.execute(
          """INSERT INTO payment_beasiswa
             (company_id, siswa_code, cat1, cat2, tanggal, amount,
              pillar, perusahaan, pam, status)
             VALUES (?,?,?,?,?,?,?,?,?,?)""",
          (company_id, "S001", "General", "Sem 1", "2026-05-26",
           5000000, "ETF", "PT. SMART Tbk", pam_no, "draft")
      )
      conn.commit()


  def test_get_pam_payments_returns_students():
      conn = get_conn()
      _seed_siswa_and_payment(conn, COMPANY_ID, "PAM-052-ETF-05-2026")
      conn.close()
      rows = get_pam_payments("PAM-052-ETF-05-2026", COMPANY_ID)
      assert len(rows) == 1
      assert rows[0]["nama"] == "Harry Santoso"
      assert rows[0]["bank"] == "BCA"
      assert rows[0]["amount"] == 5000000


  def test_get_pam_payments_empty_for_wrong_company():
      conn = get_conn()
      _seed_siswa_and_payment(conn, COMPANY_ID, "PAM-052-ETF-05-2026")
      conn.close()
      rows = get_pam_payments("PAM-052-ETF-05-2026", 999)
      assert rows == []
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  cd C:/Financehub/app && python -m pytest tests/test_pam_service.py::test_get_pam_payments_returns_students -v
  ```

  Expected: `FAILED` with `ImportError` or `AttributeError`

- [ ] **Step 3: Implement `get_pam_payments()` in service.py**

  Open `app/modules/payment_memo/service.py`. Add this function just before `export_memo_pdf` (around line 500):

  ```python
  def get_pam_payments(pam_no: str, company_id: int) -> list:
      conn = get_conn()
      rows = [dict(r) for r in conn.execute(
          """SELECT pb.id, pb.siswa_code, pb.cat1, pb.cat2,
                    pb.amount, pb.tanggal,
                    s.nama, s.bank, s.norek, s.namarek
             FROM payment_beasiswa pb
             LEFT JOIN siswa s
               ON s.company_id = pb.company_id AND s.code = pb.siswa_code
             WHERE pb.pam = ? AND pb.company_id = ?
             ORDER BY pb.id""",
          (pam_no, company_id)
      ).fetchall()]
      conn.close()
      return rows
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  cd C:/Financehub/app && python -m pytest tests/test_pam_service.py::test_get_pam_payments_returns_students tests/test_pam_service.py::test_get_pam_payments_empty_for_wrong_company -v
  ```

  Expected: both `PASSED`

- [ ] **Step 5: Run full suite to check no regressions**

  ```bash
  cd C:/Financehub/app && python -m pytest tests/ -v --tb=short
  ```

  Expected: all tests pass

- [ ] **Step 6: Commit**

  ```bash
  git add app/modules/payment_memo/service.py app/tests/test_pam_service.py
  git commit -m "feat(pam): add get_pam_payments() service function"
  ```

---

## Task 3: `exports.py` — PDF export

**Files:**
- Create: `app/modules/payment_memo/exports.py`
- Create: `app/tests/test_pam_exports.py`

- [ ] **Step 1: Write failing test**

  Create `app/tests/test_pam_exports.py`:

  ```python
  # tests/test_pam_exports.py
  import os, sys, io, pytest
  sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
  import config
  config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

  from database import init_db, get_conn
  from modules.payment_memo.exports import export_pam_pdf

  COMPANY_ID   = 2
  COMPANY_CODE = "ETF"

  @pytest.fixture(autouse=True)
  def clean_db():
      if os.path.exists(config.DB_PATH):
          os.remove(config.DB_PATH)
      init_db()
      _seed()
      yield
      if os.path.exists(config.DB_PATH):
          os.remove(config.DB_PATH)


  def _seed():
      conn = get_conn()
      conn.execute(
          """INSERT INTO pam_records
             (company_id, pam_no, pam_date, gl_account, cost_center, pt,
              requestors_name, keterangan, total_amount, due_date, status, created_at)
             VALUES (?,?,?,?,?,?,?,?,?,?,'draft',?)""",
          (COMPANY_ID, "PAM-001-ETF-05-2026", "2026-05-26", "70110230",
           "1008C1POFF", "PT. SMART Tbk", "Jany Turkanda",
           "Harry Santoso", 5000000, "2026-06-26", "2026-05-26T10:00:00")
      )
      conn.execute(
          """INSERT INTO siswa (company_id, code, nama, bank, norek, namarek,
             jenjang, program, status)
             VALUES (?,?,?,?,?,?,?,?,?)""",
          (COMPANY_ID, "S001", "Harry Santoso", "BCA", "1234567890",
           "Harry Santoso", "S1", "SMART", "Aktif")
      )
      conn.execute(
          """INSERT INTO payment_beasiswa
             (company_id, siswa_code, cat1, cat2, tanggal, amount,
              pillar, perusahaan, pam, status)
             VALUES (?,?,?,?,?,?,?,?,?,?)""",
          (COMPANY_ID, "S001", "General", "Sem 1", "2026-05-26",
           5000000, "ETF", "PT. SMART Tbk", "PAM-001-ETF-05-2026", "draft")
      )
      conn.commit()
      conn.close()


  def test_export_pam_pdf_returns_bytes():
      result = export_pam_pdf(1, COMPANY_ID, "Hong Tjhin", "Tenti Kidjo")
      assert isinstance(result, bytes)
      assert len(result) > 1000
      assert result[:4] == b'%PDF'


  def test_export_pam_pdf_not_found_raises():
      with pytest.raises(ValueError, match="PAM record tidak ditemukan"):
          export_pam_pdf(999, COMPANY_ID, "A", "B")
  ```

- [ ] **Step 2: Run test to verify it fails**

  ```bash
  cd C:/Financehub/app && python -m pytest tests/test_pam_exports.py::test_export_pam_pdf_returns_bytes -v
  ```

  Expected: `FAILED` with `ModuleNotFoundError: No module named 'modules.payment_memo.exports'`

- [ ] **Step 3: Create `app/modules/payment_memo/exports.py` with `export_pam_pdf()`**

  Create the file with this full content:

  ```python
  """PAM export helpers — PDF (ReportLab) and Excel (openpyxl)."""
  import io
  import config
  from datetime import datetime
  from reportlab.lib import colors
  from reportlab.lib.pagesizes import A4
  from reportlab.lib.units import cm
  from reportlab.lib.styles import ParagraphStyle
  from reportlab.platypus import (
      SimpleDocTemplate, Table, TableStyle,
      Paragraph, Spacer, PageBreak,
  )
  from reportlab.lib.enums import TA_CENTER, TA_LEFT

  from modules.payment_memo.service import get_pam_detail, get_pam_payments

  _BLUE   = colors.HexColor("#1e3a5f")
  _GOLD   = colors.HexColor("#f59e0b")
  _GRAY   = colors.HexColor("#e2e8f0")
  _LGRAY  = colors.HexColor("#f8fafc")
  _WHITE  = colors.white
  _AMBER  = colors.HexColor("#fef3c7")
  _AMBER2 = colors.HexColor("#f59e0b")


  def _fmt_date(s: str) -> str:
      """'2026-05-26' → '26 May 2026'"""
      try:
          return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%-d %B %Y")
      except Exception:
          return s or ""


  def _fmt_rp(v) -> str:
      try:
          return f"Rp {float(v):,.0f}"
      except Exception:
          return str(v)


  def _style(name, **kw):
      base = ParagraphStyle(name, fontName="Helvetica", fontSize=8,
                            leading=10, **kw)
      return base


  _S_LABEL   = _style("lbl",  fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#374151"))
  _S_VAL     = _style("val",  fontSize=8.5, textColor=colors.HexColor("#1e293b"))
  _S_VAL_HI  = _style("valhi", fontName="Helvetica-Bold", fontSize=9,
                       textColor=colors.HexColor("#1e3a5f"))
  _S_SECTION = _style("sec",  fontName="Helvetica-Bold", fontSize=7.5,
                       textColor=colors.HexColor("#374151"),
                       backColor=_GRAY)
  _S_CB      = _style("cb",   fontSize=8, textColor=colors.HexColor("#1e293b"))
  _S_TITLE   = _style("ttl",  fontName="Helvetica-Bold", fontSize=13,
                       alignment=TA_CENTER, textColor=_WHITE,
                       backColor=_BLUE, spaceAfter=0)
  _S_ATCH_H  = _style("atch", fontName="Helvetica-Bold", fontSize=9,
                       textColor=_WHITE)
  _S_TH      = _style("th",   fontName="Helvetica-Bold", fontSize=8,
                       textColor=_WHITE, alignment=TA_CENTER)
  _S_TD      = _style("td",   fontSize=8, textColor=colors.HexColor("#1e293b"))
  _S_TD_R    = _style("tdr",  fontSize=8, alignment=2,
                       textColor=colors.HexColor("#1e293b"))


  # Column widths: [label_L, val_L, label_R, val_R]
  _CW = [3.8*cm, 4.7*cm, 3.8*cm, 4.7*cm]


  def _p(s, style=None):
      return Paragraph(str(s) if s is not None else "", style or _S_VAL)


  def _terlampir():
      return _p("Terlampir", _style("tl", fontName="Helvetica-Bold",
                                    fontSize=8, textColor=colors.HexColor("#92400e"),
                                    backColor=colors.HexColor("#fef3c7")))


  def _build_pam_table(pam: dict, approved_by_1: str, approved_by_2: str) -> Table:
      L = _S_LABEL
      V = _S_VAL
      VH = _S_VAL_HI
      CB = _S_CB
      SEC = _S_SECTION

      pam_date = _fmt_date(pam.get("pam_date", ""))
      due_date = _fmt_date(pam.get("due_date", ""))
      invoice_amt = _fmt_rp(pam.get("total_amount", 0))

      data = [
          # 0: PAM No | Cost Center
          [_p("PAM No.", L),
           _p(pam.get("pam_no", ""), VH),
           _p("Cost Center", L),
           _p(pam.get("cost_center", ""), V)],
          # 1: Date | GL Account
          [_p("Date", L),
           _p(pam_date, V),
           _p("GL Account", L),
           _p(str(pam.get("gl_account", "")), V)],
          # 2: Requestor | SO/SC
          [_p("Requestor's Name", L),
           _p(pam.get("requestors_name", ""), V),
           _p("SO / SC", L),
           _p("", V)],
          # 3: Department | Company
          [_p("Department", L),
           _p("-", V),
           _p("Company", L),
           _p(pam.get("pt", ""), V)],
          # 4: Business Unit header
          [_p("Business Unit", SEC), "", "", ""],
          # 5: BU checkboxes
          [_p("☐  Upstream          ☐  Downstream          ☑  Corporate", CB),
           "", "", ""],
          # 6: Type of Request header
          [_p("Type of Request", SEC), "", "", ""],
          # 7-9: request type checkboxes
          [_p("☐  Downpayment to vendor", CB), "", "", ""],
          [_p("☑  Invoice Payment – Non PO Invoice", CB), "", "", ""],
          [_p("☐  Employee Advance / Reimbursement (Fund Transfer)", CB), "", "", ""],
          # 10: Invoice Information header
          [_p("Invoice Information", SEC), "", "", ""],
          # 11: Vendor Name | Invoice/Memo No
          [_p("Vendor Name", L),
           _terlampir(),
           _p("Invoice / Memo No", L),
           _p("-", V)],
          # 12: Invoice Amount | Expected Due Date
          [_p("Invoice Amount", L),
           _p(invoice_amt, VH),
           _p("Expected Due Date", L),
           _p(due_date, V)],
          # 13: Vendor Bank Account header
          [_p("Vendor Bank Account Details", SEC), "", "", ""],
          # 14-16: bank details
          [_p("Bank Account Name", L),  _terlampir(), "", ""],
          [_p("Bank Name", L),          _terlampir(), "", ""],
          [_p("Bank Account Number", L), _terlampir(), "", ""],
      ]

      SPAN_ROWS = [4, 5, 6, 7, 8, 9, 10, 13]

      style_cmds = [
          ("FONTNAME",     (0, 0), (-1, -1), "Helvetica"),
          ("FONTSIZE",     (0, 0), (-1, -1), 8),
          ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING",   (0, 0), (-1, -1), 3),
          ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
          ("LEFTPADDING",  (0, 0), (-1, -1), 5),
          ("GRID",         (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
          # Alternate rows
          ("BACKGROUND",   (0, 0), (-1, -1), _LGRAY),
          ("BACKGROUND",   (0, 1), (-1, 1),  _WHITE),
          ("BACKGROUND",   (0, 3), (-1, 3),  _WHITE),
          # Section header backgrounds
          ("BACKGROUND",   (0, 4),  (-1, 4),  _GRAY),
          ("BACKGROUND",   (0, 6),  (-1, 6),  _GRAY),
          ("BACKGROUND",   (0, 10), (-1, 10), _GRAY),
          ("BACKGROUND",   (0, 13), (-1, 13), _GRAY),
          # Amber for checkbox rows
          ("BACKGROUND",   (0, 5),  (-1, 5),  colors.HexColor("#fffbeb")),
          ("BACKGROUND",   (0, 7),  (-1, 9),  colors.HexColor("#fffbeb")),
      ]

      for r in SPAN_ROWS:
          style_cmds.append(("SPAN", (0, r), (3, r)))
      # Bank details: value spans cols 1-3
      for r in [14, 15, 16]:
          style_cmds.append(("SPAN", (1, r), (3, r)))

      return Table(data, colWidths=_CW, style=TableStyle(style_cmds))


  def _build_signature_table(requestors_name: str,
                             approved_by_1: str,
                             approved_by_2: str) -> Table:
      L  = _S_LABEL
      V  = _S_VAL
      sp = 1.4*cm

      data = [
          [_p("Request by", L),      "", _p("Approved by", L),    ""],
          ["", "", "", ""],
          ["", "", "", ""],
          ["", "", "", ""],
          [_p(requestors_name, _style("sn", fontName="Helvetica-Bold", fontSize=8)),
           "",
           _p(f"{approved_by_1}          {approved_by_2}",
              _style("sn2", fontName="Helvetica-Bold", fontSize=8)),
           ""],
          [_p("Checked by (QA)", L), "", "", ""],
          ["", "", "", ""],
          ["", "", "", ""],
          ["", "", "", ""],
      ]

      cw = [4.25*cm, 4.25*cm, 4.25*cm, 4.25*cm]
      style_cmds = [
          ("FONTSIZE",     (0, 0), (-1, -1), 8),
          ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING",   (0, 0), (-1, -1), 3),
          ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
          ("LEFTPADDING",  (0, 0), (-1, -1), 5),
          ("GRID",         (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
          ("BACKGROUND",   (0, 0), (-1, -1), _LGRAY),
          # Merge: Request by spans cols 0-1
          ("SPAN", (0, 0), (1, 0)),
          ("SPAN", (0, 1), (1, 1)),
          ("SPAN", (0, 2), (1, 2)),
          ("SPAN", (0, 3), (1, 3)),
          ("SPAN", (0, 4), (1, 4)),
          # Merge: Approved by spans cols 2-3
          ("SPAN", (2, 0), (3, 0)),
          ("SPAN", (2, 1), (3, 1)),
          ("SPAN", (2, 2), (3, 2)),
          ("SPAN", (2, 3), (3, 3)),
          ("SPAN", (2, 4), (3, 4)),
          # Checked by (QA) spans all
          ("SPAN", (0, 5), (3, 5)),
          ("SPAN", (0, 6), (3, 6)),
          ("SPAN", (0, 7), (3, 7)),
          ("SPAN", (0, 8), (3, 8)),
          # Bottom border under signature lines
          ("LINEBELOW", (0, 3), (1, 3), 0.8, colors.HexColor("#94a3b8")),
          ("LINEBELOW", (2, 3), (3, 3), 0.8, colors.HexColor("#94a3b8")),
          ("LINEBELOW", (0, 8), (3, 8), 0.8, colors.HexColor("#94a3b8")),
      ]
      return Table(data, colWidths=cw, style=TableStyle(style_cmds))


  def export_pam_pdf(pam_id: int, company_id: int,
                     approved_by_1: str, approved_by_2: str) -> bytes:
      pam = get_pam_detail(pam_id, company_id)
      if not pam:
          raise ValueError("PAM record tidak ditemukan.")

      approved_by_1 = approved_by_1 or config.PAM_APPROVED_BY_1
      approved_by_2 = approved_by_2 or config.PAM_APPROVED_BY_2
      pam_no        = pam["pam_no"]

      payments = get_pam_payments(pam_no, company_id)

      buf = io.BytesIO()
      doc = SimpleDocTemplate(
          buf, pagesize=A4,
          leftMargin=2*cm, rightMargin=2*cm,
          topMargin=1.5*cm, bottomMargin=1.5*cm,
      )

      elems = []

      # ── Page 1: PAM Form ──────────────────────────────────────────────────────
      # Title banner
      title_data = [[_p("PAYMENT APPROVAL MEMO", _S_TITLE)]]
      title_tbl  = Table(title_data, colWidths=[17*cm])
      title_tbl.setStyle(TableStyle([
          ("BACKGROUND",     (0, 0), (-1, -1), _BLUE),
          ("LINEBELOW",      (0, 0), (-1, -1), 3, _GOLD),
          ("TOPPADDING",     (0, 0), (-1, -1), 8),
          ("BOTTOMPADDING",  (0, 0), (-1, -1), 8),
      ]))
      elems.append(title_tbl)
      elems.append(Spacer(1, 0.15*cm))

      elems.append(_build_pam_table(pam, approved_by_1, approved_by_2))
      elems.append(Spacer(1, 0.3*cm))
      elems.append(_build_signature_table(
          pam.get("requestors_name", ""), approved_by_1, approved_by_2
      ))

      # ── Page 2: Lampiran ─────────────────────────────────────────────────────
      elems.append(PageBreak())

      att_hdr = [[_p(
          f"Lampiran — Jadwal Pembayaran Beasiswa", _S_ATCH_H
      )]]
      att_sub = [[_p(
          f"{pam_no}  ·  {pam.get('pt','')}  ·  {_fmt_date(pam.get('pam_date',''))}",
          _style("atsub", fontSize=7.5, textColor=colors.HexColor("#cbd5e1"))
      )]]
      att_hdr_tbl = Table(att_hdr + att_sub, colWidths=[17*cm])
      att_hdr_tbl.setStyle(TableStyle([
          ("BACKGROUND",    (0, 0), (-1, -1), _BLUE),
          ("LINEBELOW",     (0, -1), (-1, -1), 3, _GOLD),
          ("TOPPADDING",    (0, 0), (0, 0), 7),
          ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
          ("LEFTPADDING",   (0, 0), (-1, -1), 8),
      ]))
      elems.append(att_hdr_tbl)
      elems.append(Spacer(1, 0.3*cm))

      # Student table
      headers = ["No", "Nama Siswa", "Bank", "No. Rekening",
                 "Atas Nama", "Kategori", "Kode", "Amount (Rp)"]
      rows = [[_p(h, _S_TH) for h in headers]]
      total = 0
      for i, pb in enumerate(payments, 1):
          cat = f"{pb.get('cat1','')}/{pb.get('cat2','')}"
          rows.append([
              _p(str(i), _style("n", alignment=1, fontSize=8)),
              _p(pb.get("nama") or pb.get("siswa_code", ""), _S_TD),
              _p(pb.get("bank", "") or "", _S_TD),
              _p(pb.get("norek", "") or "", _S_TD),
              _p(pb.get("namarek", "") or "", _S_TD),
              _p(cat, _S_TD),
              _p(pb.get("siswa_code", ""), _S_TD),
              _p(f"{float(pb.get('amount',0)):,.0f}", _S_TD_R),
          ])
          total += float(pb.get("amount", 0))

      rows.append([
          _p("", _S_TD), _p("", _S_TD), _p("", _S_TD),
          _p("", _S_TD), _p("", _S_TD), _p("", _S_TD),
          _p("TOTAL", _style("tot", fontName="Helvetica-Bold", fontSize=8, alignment=2)),
          _p(f"{total:,.0f}", _style("totv", fontName="Helvetica-Bold", fontSize=8, alignment=2)),
      ])

      col_w = [0.6*cm, 3.5*cm, 1.8*cm, 2.8*cm, 2.8*cm, 2.3*cm, 1.4*cm, 1.8*cm]
      att_tbl = Table(rows, colWidths=col_w, repeatRows=1)
      att_tbl.setStyle(TableStyle([
          ("BACKGROUND",     (0, 0), (-1, 0),  _BLUE),
          ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
          ("FONTSIZE",       (0, 0), (-1, -1), 8),
          ("GRID",           (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
          ("ROWBACKGROUNDS", (0, 1), (-1, -2), [_WHITE, _LGRAY]),
          ("BACKGROUND",     (0, -1), (-1, -1), colors.HexColor("#e8f0fe")),
          ("FONTNAME",       (0, -1), (-1, -1), "Helvetica-Bold"),
          ("LINEABOVE",      (0, -1), (-1, -1), 1.5, _BLUE),
          ("ALIGN",          (0, 0), (0, -1), "CENTER"),
          ("ALIGN",          (7, 0), (7, -1), "RIGHT"),
          ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING",     (0, 0), (-1, -1), 3),
          ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
          ("LEFTPADDING",    (0, 0), (-1, -1), 4),
      ]))
      elems.append(att_tbl)

      doc.build(elems)
      buf.seek(0)
      return buf.read()
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  cd C:/Financehub/app && python -m pytest tests/test_pam_exports.py -v
  ```

  Expected: `test_export_pam_pdf_returns_bytes PASSED`, `test_export_pam_pdf_not_found_raises PASSED`

- [ ] **Step 5: Commit**

  ```bash
  git add app/modules/payment_memo/exports.py app/tests/test_pam_exports.py
  git commit -m "feat(pam): export_pam_pdf() — 2-page ReportLab PDF"
  ```

---

## Task 4: `export_pam_excel()` in `exports.py`

**Files:**
- Modify: `app/modules/payment_memo/exports.py` (append)
- Modify: `app/tests/test_pam_exports.py` (append)

- [ ] **Step 1: Write failing test**

  Append to `app/tests/test_pam_exports.py`:

  ```python
  from modules.payment_memo.exports import export_pam_excel
  import zipfile  # xlsx files are zip archives


  def test_export_pam_excel_returns_bytes():
      result = export_pam_excel(1, COMPANY_ID, "Hong Tjhin", "Tenti Kidjo")
      assert isinstance(result, bytes)
      assert len(result) > 500
      # Valid xlsx = valid zip
      assert zipfile.is_zipfile(io.BytesIO(result))


  def test_export_pam_excel_has_two_sheets():
      import openpyxl
      result = export_pam_excel(1, COMPANY_ID, "Hong Tjhin", "Tenti Kidjo")
      wb = openpyxl.load_workbook(io.BytesIO(result))
      assert wb.sheetnames == ["PAM", "Lampiran"]


  def test_export_pam_excel_pam_no_in_sheet():
      import openpyxl
      result = export_pam_excel(1, COMPANY_ID, "Hong Tjhin", "Tenti Kidjo")
      wb = openpyxl.load_workbook(io.BytesIO(result))
      ws = wb["PAM"]
      values = [ws.cell(r, c).value for r in range(1, 30) for c in range(1, 10)]
      assert "PAM-001-ETF-05-2026" in values


  def test_export_pam_excel_not_found_raises():
      with pytest.raises(ValueError, match="PAM record tidak ditemukan"):
          export_pam_excel(999, COMPANY_ID, "A", "B")
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  cd C:/Financehub/app && python -m pytest tests/test_pam_exports.py::test_export_pam_excel_returns_bytes -v
  ```

  Expected: `FAILED` with `ImportError`

- [ ] **Step 3: Add `export_pam_excel()` to `exports.py`**

  Append the following to `app/modules/payment_memo/exports.py`:

  ```python
  # ─────────────────────────────────────────────────────────────────────────────
  # Excel export
  # ─────────────────────────────────────────────────────────────────────────────

  def export_pam_excel(pam_id: int, company_id: int,
                       approved_by_1: str, approved_by_2: str) -> bytes:
      import openpyxl
      from openpyxl.styles import (
          Font, PatternFill, Alignment, Border, Side, numbers
      )

      pam = get_pam_detail(pam_id, company_id)
      if not pam:
          raise ValueError("PAM record tidak ditemukan.")

      approved_by_1 = approved_by_1 or config.PAM_APPROVED_BY_1
      approved_by_2 = approved_by_2 or config.PAM_APPROVED_BY_2
      pam_no        = pam["pam_no"]
      payments      = get_pam_payments(pam_no, company_id)

      wb = openpyxl.Workbook()

      # ── Sheet 1: PAM Form ────────────────────────────────────────────────────
      ws1 = wb.active
      ws1.title = "PAM"

      blue_fill  = PatternFill("solid", fgColor="1E3A5F")
      gold_fill  = PatternFill("solid", fgColor="F59E0B")
      gray_fill  = PatternFill("solid", fgColor="E2E8F0")
      lgray_fill = PatternFill("solid", fgColor="F8FAFC")
      amber_fill = PatternFill("solid", fgColor="FEF3C7")
      white_fill = PatternFill("solid", fgColor="FFFFFF")

      def _bold_white(sz=11):
          return Font(bold=True, color="FFFFFF", size=sz, name="Arial")

      def _bold(sz=9, color="1E293B"):
          return Font(bold=True, size=sz, name="Arial", color=color)

      def _normal(sz=9, color="374151"):
          return Font(size=sz, name="Arial", color=color)

      def _center():
          return Alignment(horizontal="center", vertical="center", wrap_text=True)

      def _left():
          return Alignment(horizontal="left", vertical="center", wrap_text=True)

      thin = Side(style="thin", color="D1D5DB")
      _border = Border(left=thin, right=thin, top=thin, bottom=thin)

      def _set(cell, value, font=None, fill=None, align=None):
          cell.value = value
          if font:   cell.font   = font
          if fill:   cell.fill   = fill
          if align:  cell.alignment = align
          cell.border = _border

      # Row 1: Title
      ws1.merge_cells("A1:Q1")
      _set(ws1["A1"], "PAYMENT APPROVAL MEMO",
           font=_bold_white(13), fill=blue_fill, align=_center())
      ws1.row_dimensions[1].height = 22

      # Row 2: gold separator
      ws1.merge_cells("A2:Q2")
      ws1["A2"].fill = gold_fill
      ws1.row_dimensions[2].height = 4

      def _field_row(row, label_l, val_l, label_r, val_r):
          ws1.merge_cells(f"B{row}:D{row}")
          ws1.merge_cells(f"F{row}:J{row}")
          ws1.merge_cells(f"L{row}:N{row}")
          ws1.merge_cells(f"P{row}:Q{row}")
          _set(ws1[f"B{row}"], label_l, font=_bold(9, "374151"), fill=lgray_fill, align=_left())
          _set(ws1[f"E{row}"], ":", font=_normal(), fill=lgray_fill, align=_center())
          _set(ws1[f"F{row}"], val_l,  font=_bold(9), fill=white_fill, align=_left())
          _set(ws1[f"L{row}"], label_r, font=_bold(9, "374151"), fill=lgray_fill, align=_left())
          _set(ws1[f"O{row}"], ":", font=_normal(), fill=lgray_fill, align=_center())
          _set(ws1[f"P{row}"], val_r,  font=_bold(9), fill=white_fill, align=_left())

      _field_row(3, "PAM No.",          pam["pam_no"],
                    "Cost Center",      pam.get("cost_center", ""))
      _field_row(4, "Date",             _fmt_date(pam.get("pam_date", "")),
                    "GL Account",       str(pam.get("gl_account", "")))
      _field_row(5, "Requestor's Name", pam.get("requestors_name", ""),
                    "SO / SC",          "")
      _field_row(6, "Department",       "-",
                    "Company",          pam.get("pt", ""))

      # Business Unit section
      ws1.merge_cells("B7:Q7")
      _set(ws1["B7"], "Business Unit", font=_bold(9, "374151"), fill=gray_fill, align=_left())
      ws1.merge_cells("B8:Q8")
      _set(ws1["B8"], "☐  Upstream          ☐  Downstream          ☑  Corporate",
           font=_normal(9), fill=amber_fill, align=_left())

      # Type of Request section
      ws1.merge_cells("B9:Q9")
      _set(ws1["B9"], "Type of Request", font=_bold(9, "374151"), fill=gray_fill, align=_left())
      ws1.merge_cells("B10:Q10")
      _set(ws1["B10"], "☐  Downpayment to vendor", font=_normal(9), fill=amber_fill, align=_left())
      ws1.merge_cells("B11:Q11")
      _set(ws1["B11"], "☑  Invoice Payment – Non PO Invoice",
           font=_bold(9), fill=amber_fill, align=_left())
      ws1.merge_cells("B12:Q12")
      _set(ws1["B12"], "☐  Employee Advance / Reimbursement (Fund Transfer)",
           font=_normal(9), fill=amber_fill, align=_left())

      # Invoice Information section
      ws1.merge_cells("B13:Q13")
      _set(ws1["B13"], "Invoice Information", font=_bold(9, "374151"), fill=gray_fill, align=_left())

      def _inv_row(row, label, value, right_label="", right_val=""):
          ws1.merge_cells(f"C{row}:E{row}")
          ws1.merge_cells(f"G{row}:J{row}")
          _set(ws1[f"C{row}"], label, font=_bold(9, "374151"), fill=lgray_fill, align=_left())
          _set(ws1[f"F{row}"], ":", font=_normal(), fill=lgray_fill, align=_center())
          _set(ws1[f"G{row}"], value, font=_bold(9), fill=white_fill, align=_left())
          if right_label:
              ws1.merge_cells(f"K{row}:M{row}")
              ws1.merge_cells(f"O{row}:Q{row}")
              _set(ws1[f"K{row}"], right_label, font=_bold(9, "374151"), fill=lgray_fill, align=_left())
              _set(ws1[f"N{row}"], ":", font=_normal(), fill=lgray_fill, align=_center())
              _set(ws1[f"O{row}"], right_val, font=_bold(9), fill=white_fill, align=_left())

      _inv_row(14, "Vendor Name",       "Terlampir",
                   "Invoice / Memo No", "-")
      _inv_row(15, "Invoice Amount",    _fmt_rp(pam.get("total_amount", 0)),
                   "Expected Due Date", _fmt_date(pam.get("due_date", "")))

      # Vendor Bank Account section
      ws1.merge_cells("B16:Q16")
      _set(ws1["B16"], "Vendor Bank Account Details",
           font=_bold(9, "374151"), fill=gray_fill, align=_left())

      def _bank_row(row, label):
          ws1.merge_cells(f"C{row}:E{row}")
          ws1.merge_cells(f"G{row}:Q{row}")
          _set(ws1[f"C{row}"], label, font=_bold(9, "374151"), fill=lgray_fill, align=_left())
          _set(ws1[f"F{row}"], ":", font=_normal(), fill=lgray_fill, align=_center())
          _set(ws1[f"G{row}"], "Terlampir", font=_bold(9, "92400E"), fill=amber_fill, align=_left())

      _bank_row(17, "Bank Account Name")
      _bank_row(18, "Bank Name")
      _bank_row(19, "Bank Account Number")

      # Signature rows
      ws1.merge_cells("B20:Q20")
      ws1["B20"].fill = gray_fill

      ws1.merge_cells(f"B21:F24")
      _set(ws1["B21"], "Request by", font=_bold(9, "374151"), fill=lgray_fill, align=_left())
      ws1.merge_cells(f"H21:Q24")
      _set(ws1["H21"], "Approved by", font=_bold(9, "374151"), fill=lgray_fill, align=_left())

      ws1.merge_cells(f"B25:F25")
      _set(ws1["B25"], pam.get("requestors_name", ""),
           font=_bold(10, "1E3A5F"), fill=lgray_fill, align=_left())
      ws1.merge_cells(f"H25:Q25")
      _set(ws1["H25"], f"{approved_by_1}          {approved_by_2}",
           font=_bold(10, "1E3A5F"), fill=lgray_fill, align=_left())

      ws1.merge_cells("B26:Q26")
      _set(ws1["B26"], "Checked by (QA)", font=_bold(9, "374151"), fill=lgray_fill, align=_left())
      ws1.merge_cells("B27:Q30")
      ws1["B27"].fill = white_fill

      # Column widths
      for col, w in zip("ABCDEFGHIJKLMNOPQ",
                        [1, 8, 5, 5, 5, 2, 10, 5, 5, 5, 5, 5, 5, 5, 2, 10, 10]):
          ws1.column_dimensions[col].width = w

      # ── Sheet 2: Lampiran ────────────────────────────────────────────────────
      ws2 = wb.create_sheet("Lampiran")

      ws2.merge_cells("A1:H1")
      _set(ws2["A1"], "Lampiran — Jadwal Pembayaran Beasiswa",
           font=_bold_white(11), fill=blue_fill, align=_left())
      ws2.row_dimensions[1].height = 18

      ws2.merge_cells("A2:H2")
      _set(ws2["A2"],
           f"{pam_no}  ·  {pam.get('pt','')}  ·  {_fmt_date(pam.get('pam_date',''))}",
           font=Font(size=8, color="CBD5E1", name="Arial"), fill=blue_fill, align=_left())

      hdr = ["No", "Nama Siswa", "Bank", "No. Rekening",
             "Atas Nama", "Kategori", "Kode", "Amount (Rp)"]
      for c, h in enumerate(hdr, 1):
          cell = ws2.cell(3, c, h)
          cell.font   = _bold_white(9)
          cell.fill   = blue_fill
          cell.alignment = _center()
          cell.border = _border

      total = 0
      for i, pb in enumerate(payments, 1):
          r = 3 + i
          cat = f"{pb.get('cat1','')}/{pb.get('cat2','')}"
          row_data = [
              i,
              pb.get("nama") or pb.get("siswa_code", ""),
              pb.get("bank") or "",
              pb.get("norek") or "",
              pb.get("namarek") or "",
              cat,
              pb.get("siswa_code", ""),
              float(pb.get("amount", 0)),
          ]
          fill = white_fill if i % 2 else lgray_fill
          for c, v in enumerate(row_data, 1):
              cell = ws2.cell(r, c, v)
              cell.font      = _normal(9)
              cell.fill      = fill
              cell.alignment = _center() if c in (1, 3) else _left()
              cell.border    = _border
              if c == 8:
                  cell.alignment = Alignment(horizontal="right", vertical="center")
                  cell.number_format = '#,##0'
          total += float(pb.get("amount", 0))

      # Total row
      tr = 3 + len(payments) + 1
      ws2.cell(tr, 7, "TOTAL").font       = _bold(9)
      ws2.cell(tr, 7).fill               = PatternFill("solid", fgColor="E8F0FE")
      ws2.cell(tr, 7).alignment          = Alignment(horizontal="right", vertical="center")
      ws2.cell(tr, 7).border             = _border
      tc = ws2.cell(tr, 8, total)
      tc.font         = _bold(9)
      tc.fill         = PatternFill("solid", fgColor="E8F0FE")
      tc.alignment    = Alignment(horizontal="right", vertical="center")
      tc.number_format = '#,##0'
      tc.border       = _border

      # Column widths for lampiran sheet
      for col, w in zip("ABCDEFGH", [5, 22, 12, 16, 18, 18, 10, 14]):
          ws2.column_dimensions[col].width = w

      buf = io.BytesIO()
      wb.save(buf)
      buf.seek(0)
      return buf.read()
  ```

- [ ] **Step 4: Run all export tests**

  ```bash
  cd C:/Financehub/app && python -m pytest tests/test_pam_exports.py -v
  ```

  Expected: all 6 tests `PASSED`

- [ ] **Step 5: Run full suite**

  ```bash
  cd C:/Financehub/app && python -m pytest tests/ -v --tb=short 2>&1 | tail -5
  ```

  Expected: all tests pass

- [ ] **Step 6: Commit**

  ```bash
  git add app/modules/payment_memo/exports.py app/tests/test_pam_exports.py
  git commit -m "feat(pam): export_pam_excel() — 2-sheet openpyxl workbook"
  ```

---

## Task 5: Export routes

**Files:**
- Modify: `app/modules/payment_memo/routes.py`

- [ ] **Step 1: Add import at top of routes.py**

  After the existing imports, add:

  ```python
  from modules.payment_memo.exports import export_pam_pdf, export_pam_excel
  ```

- [ ] **Step 2: Add 2 export routes**

  Append after the existing `/pam/<int:pam_id>/cancel` route:

  ```python
  @bp.route("/pam/<int:pam_id>/export/pdf")
  @role_required("requester", "verificator", "releaser")
  def export_pam_pdf_route(pam_id):
      company_id    = session.get("company_id")
      approved_by_1 = request.args.get("approved_by_1", "").strip()
      approved_by_2 = request.args.get("approved_by_2", "").strip()
      try:
          pdf_bytes = export_pam_pdf(pam_id, company_id, approved_by_1, approved_by_2)
      except ValueError as e:
          return jsonify({"ok": False, "pesan": str(e)}), 404
      from modules.payment_memo.service import get_pam_detail
      pam      = get_pam_detail(pam_id, company_id)
      filename = f"{pam['pam_no']}.pdf" if pam else f"pam_{pam_id}.pdf"
      return send_file(
          io.BytesIO(pdf_bytes),
          mimetype="application/pdf",
          download_name=filename,
          as_attachment=True,
      )


  @bp.route("/pam/<int:pam_id>/export/excel")
  @role_required("requester", "verificator", "releaser")
  def export_pam_excel_route(pam_id):
      company_id    = session.get("company_id")
      approved_by_1 = request.args.get("approved_by_1", "").strip()
      approved_by_2 = request.args.get("approved_by_2", "").strip()
      try:
          xls_bytes = export_pam_excel(pam_id, company_id, approved_by_1, approved_by_2)
      except ValueError as e:
          return jsonify({"ok": False, "pesan": str(e)}), 404
      from modules.payment_memo.service import get_pam_detail
      pam      = get_pam_detail(pam_id, company_id)
      filename = f"{pam['pam_no']}.xlsx" if pam else f"pam_{pam_id}.xlsx"
      return send_file(
          io.BytesIO(xls_bytes),
          mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          download_name=filename,
          as_attachment=True,
      )
  ```

- [ ] **Step 3: Verify the routes register without error**

  ```bash
  cd C:/Financehub/app && python -c "
  from app import create_app
  app = create_app()
  rules = [str(r) for r in app.url_map.iter_rules() if 'pam' in str(r) and 'export' in str(r)]
  print(rules)
  "
  ```

  Expected output contains:
  ```
  ['/payment-memo/pam/<int:pam_id>/export/pdf', '/payment-memo/pam/<int:pam_id>/export/excel']
  ```

  > If `create_app` import path differs, try: `from modules.payment_memo.routes import bp; print([r for r in bp.deferred_functions])`

- [ ] **Step 4: Run full suite**

  ```bash
  cd C:/Financehub/app && python -m pytest tests/ -v --tb=short 2>&1 | tail -5
  ```

  Expected: all tests pass

- [ ] **Step 5: Commit**

  ```bash
  git add app/modules/payment_memo/routes.py
  git commit -m "feat(pam): add PDF and Excel export routes"
  ```

---

## Task 6: Frontend — Draft Memo tab

**Files:**
- Modify: `app/templates/payment_memo/index.html`

- [ ] **Step 1: Add tab button**

  In `index.html`, locate:
  ```html
  <button class="tab-btn" data-tab="tab-pam">PAM Records</button>
  ```
  Add after it:
  ```html
  <button class="tab-btn" data-tab="tab-draft-memo">Draft Memo</button>
  ```

- [ ] **Step 2: Add JS config variables in the `<script>` block**

  Locate the existing `<script>` block that begins with:
  ```javascript
  const CURRENT_ROLE = {{ current_role | tojson }};
  ```
  Add two lines after it:
  ```javascript
  const PAM_APPROVED_BY_1 = {{ pam_approved_by_1 | tojson }};
  const PAM_APPROVED_BY_2 = {{ pam_approved_by_2 | tojson }};
  ```

- [ ] **Step 3: Add the tab panel HTML**

  Just before `</div><!-- end data-tabs -->` (the line after `</div>` that closes `id="tab-pam"`), add:

  ```html
  <!-- Draft Memo Tab -->
  <div class="tab-panel" id="tab-draft-memo">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;flex-wrap:wrap">
      <label style="font-size:13px;font-weight:600;color:#374151;white-space:nowrap">PAM No:</label>
      <div style="position:relative;flex:1;max-width:380px">
        <input id="dm-pam-search" type="text" autocomplete="off"
               placeholder="Ketik PAM No atau nama PT..."
               oninput="dmSearchDebounced()"
               style="width:100%;border:1px solid #3b82f6;border-radius:6px;padding:6px 10px;font-size:13px;background:#eff6ff;color:#1e40af;font-weight:600;box-sizing:border-box">
        <div id="dm-pam-dropdown"
             style="display:none;position:absolute;top:100%;left:0;right:0;z-index:500;background:#fff;border:1px solid #e5e7eb;border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,.12);margin-top:2px;max-height:200px;overflow-y:auto">
        </div>
      </div>
      <div id="dm-approved-bar" style="display:none;align-items:center;gap:8px;flex-wrap:wrap">
        <label style="font-size:12px;font-weight:600;color:#374151">Approved by:</label>
        <input id="dm-ab1" type="text" style="border:1px solid #d1d5db;border-radius:4px;padding:4px 8px;font-size:12px;width:130px">
        <input id="dm-ab2" type="text" style="border:1px solid #d1d5db;border-radius:4px;padding:4px 8px;font-size:12px;width:130px">
        <span style="font-size:11px;color:#94a3b8">(dari config, bisa diubah)</span>
      </div>
      <div id="dm-export-btns" style="display:none;margin-left:auto;display:none;gap:6px">
        <button onclick="dmExportPDF()"
                style="background:#dc2626;color:#fff;border:none;border-radius:5px;padding:5px 14px;font-size:12px;font-weight:700;cursor:pointer">↓ PDF</button>
        <button onclick="dmExportExcel()"
                style="background:#16a34a;color:#fff;border:none;border-radius:5px;padding:5px 14px;font-size:12px;font-weight:700;cursor:pointer">↓ Excel</button>
      </div>
    </div>
    <div id="dm-form-preview"></div>
  </div>
  ```

- [ ] **Step 4: Add JavaScript for the Draft Memo tab**

  Append the following block inside the existing `<script>` tag (before the closing `</script>`):

  ```javascript
  // ── Draft Memo Tab ────────────────────────────────────────────────────────
  let _dmPamId = null;
  let _dmSearchTimer = null;

  function dmSearchDebounced() {
    clearTimeout(_dmSearchTimer);
    _dmSearchTimer = setTimeout(dmSearch, 300);
  }

  async function dmSearch() {
    const q = document.getElementById('dm-pam-search').value.trim();
    const dd = document.getElementById('dm-pam-dropdown');
    if (!q) { dd.style.display = 'none'; return; }
    const resp = await apiFetch(`/payment-memo/pam?search=${encodeURIComponent(q)}`);
    const data = await resp.json();
    if (!data.ok || !data.rows.length) { dd.style.display = 'none'; return; }
    dd.innerHTML = data.rows.slice(0, 10).map(r =>
      `<div onclick="dmSelectPAM(${r.id}, '${esc(r.pam_no)}')"
            style="padding:7px 12px;cursor:pointer;font-size:12px;border-bottom:1px solid #f1f5f9"
            onmouseover="this.style.background='#eff6ff'" onmouseout="this.style.background=''">
        <strong style="color:#1d4ed8">${esc(r.pam_no)}</strong>
        <span style="color:#64748b;margin-left:6px">${esc(r.pt)}</span>
        <span style="float:right;color:#374151;font-weight:600">Rp ${fmtRupiah(r.total_amount)}</span>
      </div>`
    ).join('');
    dd.style.display = 'block';
  }

  async function dmSelectPAM(pamId, pamNo) {
    document.getElementById('dm-pam-search').value = pamNo;
    document.getElementById('dm-pam-dropdown').style.display = 'none';
    _dmPamId = pamId;

    const resp = await apiFetch(`/payment-memo/pam/${pamId}/detail`);
    const data = await resp.json();
    if (!data.ok) { showToast('Gagal memuat PAM detail.', 'error'); return; }

    const p = data.data;
    document.getElementById('dm-ab1').value = PAM_APPROVED_BY_1;
    document.getElementById('dm-ab2').value = PAM_APPROVED_BY_2;

    const abBar = document.getElementById('dm-approved-bar');
    abBar.style.display = 'flex';

    const expBtns = document.getElementById('dm-export-btns');
    expBtns.style.display = 'flex';

    document.getElementById('dm-form-preview').innerHTML = dmRenderForm(p);
  }

  function dmRenderForm(p) {
    const fmtDate = s => {
      if (!s) return '';
      const d = new Date(s);
      return isNaN(d) ? s : d.toLocaleDateString('en-GB', {day:'numeric',month:'long',year:'numeric'});
    };
    const cb  = checked => checked
      ? '<span style="display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;border:1.5px solid #1e3a5f;background:#dbeafe;font-size:10px;font-weight:900;color:#1e3a5f;margin-right:4px">✓</span>'
      : '<span style="display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;border:1.5px solid #64748b;font-size:10px;color:transparent;margin-right:4px"> </span>';
    const terlampir = '<span style="background:#fef3c7;border:1px solid #fcd34d;border-radius:3px;padding:1px 6px;font-size:11px;font-weight:700;color:#92400e">Terlampir</span>';

    const field = (lbl, val, bold=false) =>
      `<div style="display:flex;align-items:stretch;border-bottom:1px solid #f1f5f9">
        <div style="background:#f8fafc;padding:5px 8px;font-weight:700;font-size:11px;color:#374151;min-width:140px;border-right:1px solid #e2e8f0;display:flex;align-items:center">${esc(lbl)}</div>
        <div style="padding:5px 8px;font-size:11px;color:#1e293b;flex:1;${bold?'font-weight:700':''}display:flex;align-items:center">
          <span style="color:#94a3b8;margin-right:4px">:</span>${val}
        </div>
      </div>`;

    const sectionH = (title) =>
      `<div style="background:#e2e8f0;padding:4px 8px;font-weight:700;font-size:10px;color:#374151;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid #d1d5db">
        ${title}
      </div>`;

    const cbRow = (label, checked=false) =>
      `<div style="padding:4px 8px;font-size:11px;background:#fffbeb;border-bottom:1px solid #f1f5f9;display:flex;align-items:center">
        ${cb(checked)}${label}
      </div>`;

    return `
    <div style="border:1px solid #94a3b8;border-radius:4px;overflow:hidden;font-family:Arial,sans-serif;max-width:860px">
      <!-- Title -->
      <div style="background:#1e3a5f;color:#fff;text-align:center;font-size:14px;font-weight:900;padding:10px;letter-spacing:2px;border-bottom:3px solid #f59e0b">
        PAYMENT APPROVAL MEMO
      </div>
      <!-- Fields grid -->
      <div style="display:grid;grid-template-columns:1fr 1fr;border-bottom:1px solid #e2e8f0">
        <div style="border-right:1px solid #e2e8f0">
          ${field('PAM No.', `<span style="font-family:monospace;color:#1d4ed8;font-weight:700">${esc(p.pam_no)}</span>`, true)}
          ${field('Date', fmtDate(p.pam_date))}
          ${field("Requestor's Name", esc(p.requestors_name))}
          ${field('Department', '-')}
        </div>
        <div>
          ${field('Cost Center', esc(p.cost_center))}
          ${field('GL Account', esc(p.gl_account))}
          ${field('SO / SC', '')}
          ${field('Company', esc(p.pt))}
        </div>
      </div>
      <!-- Business Unit -->
      ${sectionH('Business Unit')}
      <div style="padding:5px 8px;font-size:11px;background:#fffbeb;border-bottom:1px solid #f1f5f9;display:flex;gap:20px">
        <span>${cb(false)} Upstream</span>
        <span>${cb(false)} Downstream</span>
        <span>${cb(true)} Corporate</span>
      </div>
      <!-- Type of Request -->
      ${sectionH('Type of Request')}
      ${cbRow('Downpayment to vendor', false)}
      ${cbRow('Invoice Payment – Non PO Invoice', true)}
      ${cbRow('Employee Advance / Reimbursement (Fund Transfer)', false)}
      <!-- Invoice Information -->
      ${sectionH('Invoice Information')}
      <div style="display:grid;grid-template-columns:1fr 1fr;border-bottom:1px solid #e2e8f0">
        <div style="border-right:1px solid #e2e8f0">
          ${field('Vendor Name', terlampir)}
          ${field('Invoice Amount', `<strong style="color:#1e3a5f">Rp ${fmtRupiah(p.total_amount)}</strong>`, true)}
        </div>
        <div>
          ${field('Invoice / Memo No', '-')}
          ${field('Expected Due Date', fmtDate(p.due_date))}
        </div>
      </div>
      <!-- Vendor Bank Account -->
      ${sectionH('Vendor Bank Account Details')}
      ${field('Bank Account Name', terlampir)}
      ${field('Bank Name', terlampir)}
      ${field('Bank Account Number', terlampir)}
      <!-- Signatures -->
      <div style="display:grid;grid-template-columns:1fr 1fr;border-top:1px solid #e2e8f0">
        <div style="padding:8px 10px;border-right:1px solid #e2e8f0">
          <div style="font-size:10px;font-weight:700;color:#374151;background:#f8fafc;padding:3px 5px;margin-bottom:28px">Request by</div>
          <div style="font-size:11px;font-weight:700;color:#1e3a5f;border-top:1px solid #94a3b8;padding-top:3px">${esc(p.requestors_name)}</div>
        </div>
        <div style="padding:8px 10px">
          <div style="font-size:10px;font-weight:700;color:#374151;background:#f8fafc;padding:3px 5px;margin-bottom:28px">Approved by</div>
          <div style="font-size:11px;font-weight:700;color:#1e3a5f;border-top:1px solid #94a3b8;padding-top:3px">
            ${esc(document.getElementById('dm-ab1').value)}
            &nbsp;&nbsp;&nbsp;
            ${esc(document.getElementById('dm-ab2').value)}
          </div>
        </div>
      </div>
      <div style="padding:6px 10px;font-weight:700;font-size:10px;color:#374151;background:#f8fafc;border-top:1px solid #e2e8f0">Checked by (QA)</div>
      <div style="height:36px;border-top:1px solid #e2e8f0"></div>
      <div style="padding:4px 8px;font-size:10px;color:#94a3b8;font-style:italic;border-top:1px solid #f1f5f9">
        ▸ Lampiran jadwal siswa: halaman 2 di PDF / sheet "Lampiran" di Excel
      </div>
    </div>`;
  }

  function _dmExportUrl(format) {
    if (!_dmPamId) { showToast('Pilih PAM No terlebih dahulu.', 'error'); return null; }
    const ab1 = encodeURIComponent(document.getElementById('dm-ab1').value || '');
    const ab2 = encodeURIComponent(document.getElementById('dm-ab2').value || '');
    return `/payment-memo/pam/${_dmPamId}/export/${format}?approved_by_1=${ab1}&approved_by_2=${ab2}`;
  }

  function dmExportPDF() {
    const url = _dmExportUrl('pdf');
    if (url) window.open(url, '_blank');
  }

  function dmExportExcel() {
    const url = _dmExportUrl('excel');
    if (url) window.open(url, '_blank');
  }

  // Close PAM dropdown when clicking outside
  document.addEventListener('click', e => {
    const dd = document.getElementById('dm-pam-dropdown');
    if (dd && !e.target.closest('#dm-pam-search') && !e.target.closest('#dm-pam-dropdown')) {
      dd.style.display = 'none';
    }
  });
  ```

- [ ] **Step 5: Manual smoke test**

  1. Start the server: `cd C:/Financehub/app && python app.py`
  2. Log in and navigate to **Payment Memo → Draft Memo** tab
  3. Type a PAM No fragment → dropdown appears with matching records
  4. Click a record → form preview renders with all fields
  5. Verify "Approved by" fields are pre-filled from config
  6. Click **↓ PDF** → file downloads, opens as 2-page document
  7. Click **↓ Excel** → file downloads, opens with 2 sheets (PAM + Lampiran)
  8. Edit "Approved by" → click PDF again → verify new name appears in downloaded file

- [ ] **Step 6: Run full test suite**

  ```bash
  cd C:/Financehub/app && python -m pytest tests/ -v --tb=short 2>&1 | tail -10
  ```

  Expected: all tests pass (count should be ≥ previous + 6 new)

- [ ] **Step 7: Commit**

  ```bash
  git add app/templates/payment_memo/index.html
  git commit -m "feat(pam): Draft Memo tab — PAM search, form preview, PDF/Excel export"
  ```

---

## Self-Review Checklist

- [x] **Spec coverage**: Config defaults ✓, get_pam_payments ✓, PDF 2 pages ✓, Excel 2 sheets ✓, routes ✓, frontend tab ✓, Approved By editable ✓, fallback to config ✓
- [x] **No placeholders**: All code blocks contain full implementations
- [x] **Type consistency**: `export_pam_pdf(pam_id, company_id, approved_by_1, approved_by_2)` used consistently in task 3, task 5, and test file; same for `export_pam_excel`
- [x] **`get_pam_payments` defined in Task 2, imported in `exports.py` Task 3** — dependency order is correct
- [x] **`_fmt_date` handles Windows** — uses `%-d` on Linux; add fallback for Windows (strftime `%#d`)
  - Fix in exports.py Task 3: replace `"%-d %B %Y"` with `"%d %B %Y"` and strip leading zero in Python: `dt.strftime("%d %B %Y").lstrip("0")` — simpler and cross-platform

> **Windows date format fix:** In `_fmt_date()`, use:
> ```python
> return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d %B %Y").lstrip("0")
> ```
> instead of `"%-d %B %Y"` (Linux-only).
