# Draft Memo Dynamic Editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every field in the Draft Memo tab editable inline, with PDF/Excel exports that reflect whatever the user edited, plus a collapsible Lampiran section showing the payment schedule.

**Architecture:** Inline `<input>` and `<checkbox>` elements replace static text inside the rendered PAM form; on export, `collectDmFields()` harvests all values from the DOM and POSTs them to two new backend endpoints (`/export/pdf-custom`, `/export/excel-custom`) that generate files from the posted data rather than re-reading the DB. The existing GET export routes are left untouched.

**Tech Stack:** Flask (Python), ReportLab (PDF), openpyxl (Excel), vanilla JS, Jinja2 templates.

---

## Working directory

All commands run from `C:\Financehub\app`.
Test runner: `python -m pytest tests/ -q --tb=short`
Baseline: 58 passing tests.

---

## Task 1 — Extend `/pam/{id}/detail` route to include payments

**Files:**
- Modify: `modules/payment_memo/routes.py` (import + route handler at line 155)
- Test: `tests/test_memo_api.py`

- [ ] **Step 1: Write the failing test**

  Add to `tests/test_memo_api.py`:

  ```python
  def test_pam_detail_includes_payments(client):
      from modules.payment_memo.service import create_pam_record
      from database import get_conn
      conn = get_conn()
      try:
          pam_no = create_pam_record(conn, 2, "ETF", {
              "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
              "keterangan": "Test", "total_amount": 5000000.0, "payment_ids": [],
          })
          conn.execute(
              "INSERT INTO siswa (company_id,code,nama,bank,norek,namarek,jenjang,program,status)"
              " VALUES (?,?,?,?,?,?,?,?,?)",
              (2, "S001", "Budi", "BCA", "123456", "Budi", "S1", "SMART", "Aktif"),
          )
          conn.execute(
              "INSERT INTO payment_beasiswa"
              " (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,pam,status)"
              " VALUES (?,?,?,?,?,?,?,?,?,?)",
              (2, "S001", "General", "Sem 1", "2026-05-31", 5000000, "ETF", "PT. SMART Tbk", pam_no, "draft"),
          )
          conn.commit()
          pam_id = conn.execute(
              "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
          ).fetchone()["id"]
      finally:
          conn.close()

      token = _login(client)
      with client.session_transaction() as sess:
          sess["company_id"] = 2
      rv = client.get(f"/payment-memo/pam/{pam_id}/detail",
                      headers={"Authorization": f"Bearer {token}"})
      assert rv.status_code == 200
      body = rv.get_json()
      assert body["ok"] is True
      assert "payments" in body["data"]
      assert len(body["data"]["payments"]) == 1
      assert body["data"]["payments"][0]["siswa_code"] == "S001"
  ```

- [ ] **Step 2: Run test to confirm it fails**

  ```
  python -m pytest tests/test_memo_api.py::test_pam_detail_includes_payments -v
  ```
  Expected: FAIL — `AssertionError: assert 'payments' in ...`

- [ ] **Step 3: Add `get_pam_payments` to the import in `routes.py`**

  Current import block (lines 4–12):
  ```python
  from modules.payment_memo.service import (
      get_draft_payments, create_memo, get_memo_list, get_memo_detail,
      update_memo_status, export_memo_pdf,
      get_pam_list, get_coa_list, update_pam_gl_account,
      update_pam_status, update_pam_record,
      get_pam_detail, update_pam_and_application,
      get_draft_payment_detail, update_draft_and_linked,
      delete_payment_beasiswa, cancel_pam_record,
  )
  ```

  Replace with:
  ```python
  from modules.payment_memo.service import (
      get_draft_payments, create_memo, get_memo_list, get_memo_detail,
      update_memo_status, export_memo_pdf,
      get_pam_list, get_coa_list, update_pam_gl_account,
      update_pam_status, update_pam_record,
      get_pam_detail, get_pam_payments, update_pam_and_application,
      get_draft_payment_detail, update_draft_and_linked,
      delete_payment_beasiswa, cancel_pam_record,
  )
  ```

- [ ] **Step 4: Extend the detail route handler**

  Current handler (lines 155–161):
  ```python
  @bp.route("/pam/<int:pam_id>/detail")
  @role_required("requester", "verificator", "releaser")
  def get_pam_detail_route(pam_id):
      detail = get_pam_detail(pam_id, session.get("company_id", 0))
      if not detail:
          return jsonify({"ok": False, "pesan": "PAM record tidak ditemukan."}), 404
      return jsonify({"ok": True, "data": detail})
  ```

  Replace with:
  ```python
  @bp.route("/pam/<int:pam_id>/detail")
  @role_required("requester", "verificator", "releaser")
  def get_pam_detail_route(pam_id):
      company_id = session.get("company_id", 0)
      detail = get_pam_detail(pam_id, company_id)
      if not detail:
          return jsonify({"ok": False, "pesan": "PAM record tidak ditemukan."}), 404
      detail["payments"] = get_pam_payments(detail["pam_no"], company_id)
      return jsonify({"ok": True, "data": detail})
  ```

- [ ] **Step 5: Run test to confirm it passes**

  ```
  python -m pytest tests/test_memo_api.py::test_pam_detail_includes_payments -v
  ```
  Expected: PASS

- [ ] **Step 6: Run full suite to check for regressions**

  ```
  python -m pytest tests/ -q --tb=short
  ```
  Expected: all previously-passing tests still pass (58+1).

- [ ] **Step 7: Commit**

  ```
  git add modules/payment_memo/routes.py tests/test_memo_api.py
  git commit -m "feat(pam): include payments list in detail route response"
  ```

---

## Task 2 — Add `_build_pam_table_custom()` and `export_pam_pdf_custom()` to exports.py

**Files:**
- Modify: `modules/payment_memo/exports.py` (append after line 280)
- Test: `tests/test_pam_exports.py`

- [ ] **Step 1: Write failing tests**

  Add to `tests/test_pam_exports.py`:

  ```python
  from modules.payment_memo.exports import export_pam_pdf_custom

  _CUSTOM_DATA = {
      "pam_no":           "PAM-001-ETF-05-2026",
      "pam_date":         "2026-05-26",
      "requestors_name":  "Jany Turkanda",
      "department":       "HR",
      "cost_center":      "1008C1POFF",
      "gl_account":       "70110230",
      "so_sc":            "",
      "pt":               "PT. SMART Tbk",
      "bu_upstream":      False,
      "bu_downstream":    False,
      "bu_corporate":     True,
      "type_downpayment": False,
      "type_invoice":     True,
      "type_advance":     False,
      "vendor_name":      "Terlampir",
      "invoice_memo_no":  "-",
      "total_amount":     5000000,
      "due_date":         "2026-06-26",
      "bank_account_name":"Terlampir",
      "bank_name":        "Terlampir",
      "bank_account_no":  "Terlampir",
      "approved_by_1":    "Hong Tjhin",
      "approved_by_2":    "Tenti Kidjo",
  }

  _PAYMENTS = [
      {"siswa_code": "S001", "nama": "Harry Santoso", "bank": "BCA",
       "norek": "1234567890", "namarek": "Harry Santoso",
       "cat1": "General", "cat2": "Sem 1", "amount": 5000000},
  ]

  def test_export_pam_pdf_custom_returns_pdf():
      result = export_pam_pdf_custom(_CUSTOM_DATA, _PAYMENTS)
      assert isinstance(result, bytes)
      assert result[:4] == b'%PDF'
      assert len(result) > 1000

  def test_export_pam_pdf_custom_empty_payments():
      result = export_pam_pdf_custom(_CUSTOM_DATA, [])
      assert isinstance(result, bytes)
      assert result[:4] == b'%PDF'

  def test_export_pam_pdf_custom_checkboxes_upstream():
      data = {**_CUSTOM_DATA, "bu_upstream": True, "bu_corporate": False}
      result = export_pam_pdf_custom(data, [])
      assert isinstance(result, bytes)
      assert result[:4] == b'%PDF'
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  ```
  python -m pytest tests/test_pam_exports.py::test_export_pam_pdf_custom_returns_pdf -v
  ```
  Expected: FAIL — `ImportError: cannot import name 'export_pam_pdf_custom'`

- [ ] **Step 3: Add `_build_pam_table_custom()` to `exports.py`**

  Append after the closing of `_build_signature_table()` (after line ~176), before `export_pam_pdf()`:

  ```python
  def _build_pam_table_custom(data: dict) -> Table:
      pam_date    = _fmt_date(data.get("pam_date", ""))
      due_date    = _fmt_date(data.get("due_date", ""))
      invoice_amt = _fmt_rp(data.get("total_amount", 0))

      def _cb(val):
          return "☑" if val else "☐"

      def _maybe_terlampir(val):
          if not val or val.strip().lower() == "terlampir":
              return _terlampir()
          return _p(val, _S_VAL)

      bu_row  = f"{_cb(data.get('bu_upstream'))}  Upstream          "
      bu_row += f"{_cb(data.get('bu_downstream'))}  Downstream          "
      bu_row += f"{_cb(data.get('bu_corporate'))}  Corporate"

      data_rows = [
          [_p("PAM No.", _S_LABEL), _p(data.get("pam_no", ""), _S_VAL_HI),
           _p("Cost Center", _S_LABEL), _p(data.get("cost_center", ""), _S_VAL)],
          [_p("Date", _S_LABEL), _p(pam_date, _S_VAL),
           _p("GL Account", _S_LABEL), _p(str(data.get("gl_account", "")), _S_VAL)],
          [_p("Requestor's Name", _S_LABEL), _p(data.get("requestors_name", ""), _S_VAL),
           _p("SO / SC", _S_LABEL), _p(data.get("so_sc", ""), _S_VAL)],
          [_p("Department", _S_LABEL), _p(data.get("department", "-"), _S_VAL),
           _p("Company", _S_LABEL), _p(data.get("pt", ""), _S_VAL)],
          [_p("Business Unit", _S_SECTION), "", "", ""],
          [_p(bu_row, _S_CB), "", "", ""],
          [_p("Type of Request", _S_SECTION), "", "", ""],
          [_p(f"{_cb(data.get('type_downpayment'))}  Downpayment to vendor", _S_CB),
           "", "", ""],
          [_p(f"{_cb(data.get('type_invoice'))}  Invoice Payment – Non PO Invoice", _S_CB),
           "", "", ""],
          [_p(f"{_cb(data.get('type_advance'))}  Employee Advance / Reimbursement (Fund Transfer)",
              _S_CB), "", "", ""],
          [_p("Invoice Information", _S_SECTION), "", "", ""],
          [_p("Vendor Name", _S_LABEL), _maybe_terlampir(data.get("vendor_name", "")),
           _p("Invoice / Memo No", _S_LABEL), _p(data.get("invoice_memo_no", "-"), _S_VAL)],
          [_p("Invoice Amount", _S_LABEL), _p(invoice_amt, _S_VAL_HI),
           _p("Expected Due Date", _S_LABEL), _p(due_date, _S_VAL)],
          [_p("Vendor Bank Account Details", _S_SECTION), "", "", ""],
          [_p("Bank Account Name", _S_LABEL),
           _maybe_terlampir(data.get("bank_account_name", "")), "", ""],
          [_p("Bank Name", _S_LABEL),
           _maybe_terlampir(data.get("bank_name", "")), "", ""],
          [_p("Bank Account Number", _S_LABEL),
           _maybe_terlampir(data.get("bank_account_no", "")), "", ""],
      ]

      span_rows = [4, 5, 6, 7, 8, 9, 10, 13]
      style_cmds = [
          ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
          ("FONTSIZE",      (0, 0), (-1, -1), 8),
          ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING",    (0, 0), (-1, -1), 3),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
          ("LEFTPADDING",   (0, 0), (-1, -1), 5),
          ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
          ("BACKGROUND",    (0, 0), (-1, -1), _LGRAY),
          ("BACKGROUND",    (0, 1), (-1, 1),  _WHITE),
          ("BACKGROUND",    (0, 3), (-1, 3),  _WHITE),
          ("BACKGROUND",    (0, 4),  (-1, 4),  _GRAY),
          ("BACKGROUND",    (0, 6),  (-1, 6),  _GRAY),
          ("BACKGROUND",    (0, 10), (-1, 10), _GRAY),
          ("BACKGROUND",    (0, 13), (-1, 13), _GRAY),
          ("BACKGROUND",    (0, 5),  (-1, 5),  _AMBER),
          ("BACKGROUND",    (0, 7),  (-1, 9),  _AMBER),
      ]
      for r in span_rows:
          style_cmds.append(("SPAN", (0, r), (3, r)))
      for r in [14, 15, 16]:
          style_cmds.append(("SPAN", (1, r), (3, r)))
      return Table(data_rows, colWidths=_CW, style=TableStyle(style_cmds))
  ```

- [ ] **Step 4: Add `export_pam_pdf_custom()` to `exports.py`**

  Append immediately after `_build_pam_table_custom()`:

  ```python
  def export_pam_pdf_custom(data: dict, payments: list) -> bytes:
      """Generate PAM PDF from a user-supplied data dict instead of DB."""
      approved_by_1 = data.get("approved_by_1") or config.PAM_APPROVED_BY_1
      approved_by_2 = data.get("approved_by_2") or config.PAM_APPROVED_BY_2
      pam_no        = data.get("pam_no", "")

      buf = io.BytesIO()
      doc = SimpleDocTemplate(
          buf, pagesize=A4,
          leftMargin=2*cm, rightMargin=2*cm,
          topMargin=1.5*cm, bottomMargin=1.5*cm,
      )
      elems = []

      title_tbl = Table([[_p("PAYMENT APPROVAL MEMO", _S_TITLE)]], colWidths=[17*cm])
      title_tbl.setStyle(TableStyle([
          ("BACKGROUND",    (0, 0), (-1, -1), _BLUE),
          ("LINEBELOW",     (0, 0), (-1, -1), 3, _GOLD),
          ("TOPPADDING",    (0, 0), (-1, -1), 8),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
      ]))
      elems.append(title_tbl)
      elems.append(Spacer(1, 0.15*cm))
      elems.append(_build_pam_table_custom(data))
      elems.append(Spacer(1, 0.3*cm))
      elems.append(_build_signature_table(
          data.get("requestors_name", ""), approved_by_1, approved_by_2
      ))

      elems.append(PageBreak())
      att_hdr = Table(
          [[_p("Lampiran — Jadwal Pembayaran Beasiswa", _S_ATCH_H)],
           [_p(f"{pam_no}  \xb7  {data.get('pt','')}  \xb7  {_fmt_date(data.get('pam_date',''))}",
               _style("atsub", fontSize=7.5, textColor=colors.HexColor("#cbd5e1")))]],
          colWidths=[17*cm]
      )
      att_hdr.setStyle(TableStyle([
          ("BACKGROUND",    (0, 0), (-1, -1), _BLUE),
          ("LINEBELOW",     (0, -1), (-1, -1), 3, _GOLD),
          ("TOPPADDING",    (0, 0), (0, 0), 7),
          ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
          ("LEFTPADDING",   (0, 0), (-1, -1), 8),
      ]))
      elems.append(att_hdr)
      elems.append(Spacer(1, 0.3*cm))

      hdrs = ["No", "Nama Siswa", "Bank", "No. Rekening",
              "Atas Nama", "Kategori", "Kode", "Amount (Rp)"]
      rows = [[_p(h, _S_TH) for h in hdrs]]
      total = 0.0
      for i, pb in enumerate(payments, 1):
          cat = f"{pb.get('cat1','')}/{pb.get('cat2','')}"
          rows.append([
              _p(str(i), _style("n", alignment=1, fontSize=8)),
              _p(pb.get("nama") or pb.get("siswa_code", ""), _S_TD),
              _p(pb.get("bank") or "", _S_TD),
              _p(pb.get("norek") or "", _S_TD),
              _p(pb.get("namarek") or "", _S_TD),
              _p(cat, _S_TD),
              _p(pb.get("siswa_code", ""), _S_TD),
              _p(f"{float(pb.get('amount', 0)):,.0f}", _S_TD_R),
          ])
          total += float(pb.get("amount", 0))
      rows.append([
          _p("", _S_TD), _p("", _S_TD), _p("", _S_TD), _p("", _S_TD),
          _p("", _S_TD), _p("", _S_TD),
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

- [ ] **Step 5: Run tests**

  ```
  python -m pytest tests/test_pam_exports.py::test_export_pam_pdf_custom_returns_pdf tests/test_pam_exports.py::test_export_pam_pdf_custom_empty_payments tests/test_pam_exports.py::test_export_pam_pdf_custom_checkboxes_upstream -v
  ```
  Expected: all 3 PASS

- [ ] **Step 6: Run full suite**

  ```
  python -m pytest tests/ -q --tb=short
  ```
  Expected: all previously-passing tests still pass.

- [ ] **Step 7: Commit**

  ```
  git add modules/payment_memo/exports.py tests/test_pam_exports.py
  git commit -m "feat(pam): add export_pam_pdf_custom() from user-supplied data"
  ```

---

## Task 3 — Add `export_pam_excel_custom()` to exports.py

**Files:**
- Modify: `modules/payment_memo/exports.py` (append at end)
- Test: `tests/test_pam_exports.py`

- [ ] **Step 1: Write failing tests**

  Add to `tests/test_pam_exports.py` (reuse `_CUSTOM_DATA` and `_PAYMENTS` from Task 2):

  ```python
  from modules.payment_memo.exports import export_pam_excel_custom

  def test_export_pam_excel_custom_returns_xlsx():
      import zipfile, io as _io
      result = export_pam_excel_custom(_CUSTOM_DATA, _PAYMENTS)
      assert isinstance(result, bytes)
      assert zipfile.is_zipfile(_io.BytesIO(result))

  def test_export_pam_excel_custom_has_two_sheets():
      import openpyxl, io as _io
      result = export_pam_excel_custom(_CUSTOM_DATA, _PAYMENTS)
      wb = openpyxl.load_workbook(_io.BytesIO(result))
      assert wb.sheetnames == ["PAM NEW", "Lampiran"]

  def test_export_pam_excel_custom_pam_no_in_sheet():
      import openpyxl, io as _io
      result = export_pam_excel_custom(_CUSTOM_DATA, _PAYMENTS)
      wb = openpyxl.load_workbook(_io.BytesIO(result))
      ws = wb["PAM NEW"]
      values = [ws.cell(r, c).value for r in range(1, 15) for c in range(1, 18)]
      assert "PAM-001-ETF-05-2026" in values

  def test_export_pam_excel_custom_approved_by_in_sheet():
      import openpyxl, io as _io
      result = export_pam_excel_custom(_CUSTOM_DATA, _PAYMENTS)
      wb = openpyxl.load_workbook(_io.BytesIO(result))
      ws = wb["PAM NEW"]
      values = [ws.cell(r, c).value for r in range(36, 50) for c in range(1, 12)]
      assert "Hong Tjhin" in values
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  ```
  python -m pytest tests/test_pam_exports.py::test_export_pam_excel_custom_returns_xlsx -v
  ```
  Expected: FAIL — `ImportError: cannot import name 'export_pam_excel_custom'`

- [ ] **Step 3: Add `export_pam_excel_custom()` to `exports.py`**

  Append at the end of `exports.py`:

  ```python
  def export_pam_excel_custom(data: dict, payments: list) -> bytes:
      """Generate PAM Excel (Book6 format) from a user-supplied data dict."""
      import openpyxl
      from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
      from datetime import datetime as _dt

      approved_by_1 = data.get("approved_by_1") or config.PAM_APPROVED_BY_1
      approved_by_2 = data.get("approved_by_2") or config.PAM_APPROVED_BY_2
      pam_no = data.get("pam_no", "")

      wb = openpyxl.Workbook()
      ws = wb.active
      ws.title = "PAM NEW"

      for col, w in [("A",3.0),("B",11.15),("C",1.84),("D",7.53),("E",6.43),
                     ("F",2.84),("G",9.0),("H",2.0),("J",4.53),("K",5.69),
                     ("L",4.69),("N",5.30),("O",1.15),("P",7.84)]:
          ws.column_dimensions[col].width = w

      ws.row_dimensions[9].height  = 8.25
      ws.row_dimensions[11].height = 16.5
      ws.row_dimensions[12].height = 11.25
      ws.row_dimensions[19].height = 17.25
      ws.row_dimensions[25].height = 15.0

      _thin = Side(style="thin")
      _box  = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)
      _C    = Alignment(horizontal="center", vertical="center", wrap_text=True)
      _CN   = Alignment(horizontal="center", vertical="center", wrap_text=False)
      _L    = Alignment(horizontal="left",   vertical="center")
      _R    = Alignment(horizontal="right",  vertical="center")

      def _bold(sz=11): return Font(bold=True,  size=sz)

      def _set(coord, val, font=None, align=None, border=None):
          c = ws[coord]
          c.value = val
          if font:   c.font      = font
          if align:  c.alignment = align
          if border: c.border    = border

      def _draw_box(r1, c1, r2, c2):
          for r in range(r1, r2 + 1):
              for c in range(c1, c2 + 1):
                  cell = ws.cell(r, c)
                  prev = cell.border
                  cell.border = Border(
                      top    = _thin if r == r1 else prev.top,
                      bottom = _thin if r == r2 else prev.bottom,
                      left   = _thin if c == c1 else prev.left,
                      right  = _thin if c == c2 else prev.right,
                  )

      def _dt_val(s):
          try:    return _dt.strptime(s[:10], "%Y-%m-%d")
          except: return s or ""

      pam_date = _dt_val(data.get("pam_date", ""))
      due_date = _dt_val(data.get("due_date", ""))

      ws.merge_cells("A1:Q1")
      _set("A1", "PAYMENT APPROVAL MEMO", font=_bold(11), align=_C)
      ws.merge_cells("B2:Q2")

      ws.merge_cells("L4:N4")
      _set("B4", "PAM No.",                              align=_L)
      _set("E4", ":")
      _set("F4", pam_no,                                 align=_L)
      _set("L4", "Cost Center",                          align=_R)
      _set("O4", ":",                                    align=_R)
      _set("P4", data.get("cost_center", ""),            align=_L)

      ws.merge_cells("F5:J5")
      ws.merge_cells("L5:N5")
      ws.merge_cells("P5:Q5")
      _set("B5", "Date",                                 align=_L)
      _set("E5", ":")
      _set("F5", pam_date,                               align=_L)
      ws["F5"].number_format = '[$-421]dd\\ mmmm\\ yyyy;@'
      _set("L5", "GL Account",                          align=_R)
      _set("O5", ":",                                    align=_R)
      _set("P5", data.get("gl_account", ""),            align=_L)

      ws.merge_cells("L6:N6")
      _set("B6", "Requestor's Name   ",                  align=_L)
      _set("E6", ":")
      _set("F6", data.get("requestors_name", ""),       align=_L)
      _set("L6", "SO / SC",                              align=_R)
      _set("O6", ":",                                    align=_R)
      _set("P6", data.get("so_sc", ""),                 align=_L)

      _set("B7", "Department",                           align=_L)
      _set("E7", ":")
      _set("F7", data.get("department", "-"),           align=_L)

      _set("B8", "Company",                              align=_L)
      _set("E8", ":")
      _set("F8", data.get("pt", ""),                    align=_L)

      _set("B10", "Bussiness Unit ",                     align=_L)

      ws["E11"].border = _box
      if data.get("bu_upstream"):
          _set("E11", "V", align=_CN, border=_box)
      _set("G11", "  Upstream",                          align=_L)
      ws["I11"].border = Border(right=_thin)
      ws["J11"].border = Border(top=_thin, bottom=_thin, right=_thin)
      if data.get("bu_downstream"):
          ws["J11"].value     = "V"
          ws["J11"].alignment = _CN
      _set("K11", "  Downstream",                        align=_L)
      _set("N11", "V" if data.get("bu_corporate") else "", align=_C, border=_box)
      _set("O11", "  Corporate",                         align=_L)

      _set("B13", "Type of Request ",                    align=_L)

      ws["E14"].border = _box
      if data.get("type_downpayment"):
          _set("E14", "V", align=_CN, border=_box)
      _set("G14", "  Downpayment to vendor",             align=_L)

      ws["E15"].border = _box
      if data.get("type_invoice"):
          _set("E15", "V", align=_CN, border=_box)
      _set("G15", "  Invoice Payment – Non PO Invoice", align=_L)

      ws["E16"].border = _box
      if data.get("type_advance"):
          _set("E16", "V", align=_CN, border=_box)
      _set("G16", "  Employee Advance/ Reimbursement (Fund Transfer)", align=_L)

      ws.merge_cells("B18:Q18")
      _set("B18", "Invoice Information",                 font=_bold(), align=_C)

      ws.merge_cells("I19:Q19")
      _set("G19", "Vendor Name",                         align=_R)
      _set("H19", ":",                                    align=_R)
      _set("I19", data.get("vendor_name", "Terlampir"),  align=_L)

      ws.merge_cells("I20:Q20")
      _set("G20", "Invoice/ Memorandum Number",          align=_R)
      _set("H20", ":",                                    align=_R)
      _set("I20", data.get("invoice_memo_no", "-"),      align=_L)

      ws.merge_cells("I21:L21")
      _set("G21", "Invoice Amount",                      align=_R)
      _set("H21", ":",                                    align=_R)
      _set("I21", data.get("total_amount", 0),           align=_C)
      ws["I21"].number_format = '_("Rp"* #,##0_);_("Rp"* \\(#,##0\\);_("Rp"* "-"_);_(@_)'

      ws.merge_cells("I22:O22")
      _set("G22", "Expected Due Date",                   align=_R)
      _set("H22", ":",                                    align=_R)
      _set("I22", due_date,                              align=_L)
      ws["I22"].number_format = '[$-421]dd\\ mmmm\\ yyyy;@'

      ws.merge_cells("B24:Q24")
      _set("B24", "Vendor Bank Account Details",         font=_bold(), align=_C)

      ws.merge_cells("I25:Q25")
      _set("D25", "Bank Account Name ",                  align=_L)
      _set("H25", ":")
      _set("I25", data.get("bank_account_name", "Terlampir"), align=_L)

      ws.merge_cells("I26:Q26")
      _set("D26", "Bank Name ",                          align=_L)
      _set("H26", ":")
      _set("I26", data.get("bank_name", "Terlampir"),   align=_L)

      ws.merge_cells("I27:Q27")
      _set("D27", "Bank Account Number",                 align=_L)
      _set("H27", ":")
      _set("I27", data.get("bank_account_no", "Terlampir"), align=_L)

      ws.merge_cells("I28:Q28")

      _draw_box(29, 2, 29, 6)
      _set("C29", "Request by",                          font=_bold(), align=_CN)
      _draw_box(30, 2, 33, 6)
      _draw_box(34, 2, 34, 6)
      _set("C34", data.get("requestors_name", ""),       align=_CN)

      _draw_box(36, 2, 36, 11)
      _set("E36", "Approved by",                         font=_bold(), align=_CN)
      for _r in range(36, 43):
          ws.cell(_r, 12).border = Border(left=_thin)
      _draw_box(37, 2, 41, 6)
      _draw_box(37, 7, 41, 11)
      _draw_box(42, 2, 42, 6)
      _draw_box(42, 7, 42, 11)
      _set("C42", approved_by_1,                         align=_CN)
      _set("H42", approved_by_2,                         align=_CN)

      _set("B43", "Checked by (QA)",                     font=_bold())
      _draw_box(44, 2, 48, 6)

      # ── Sheet 2: Lampiran ──────────────────────────────────────────────────
      ws2 = wb.create_sheet("Lampiran")

      blue_fill  = PatternFill("solid", fgColor="1E3A5F")
      lgray_fill = PatternFill("solid", fgColor="F8FAFC")
      white_fill = PatternFill("solid", fgColor="FFFFFF")
      thin2      = Side(style="thin", color="D1D5DB")
      _bdr2      = Border(left=thin2, right=thin2, top=thin2, bottom=thin2)
      _fw2       = lambda sz=9: Font(bold=True, color="FFFFFF", size=sz, name="Arial")
      _fb2       = lambda sz=9: Font(bold=True, size=sz, name="Arial")
      _fn2       = lambda sz=9: Font(bold=False, size=sz, name="Arial")

      ws2.merge_cells("A1:H1")
      c = ws2["A1"]
      c.value = "Lampiran — Jadwal Pembayaran Beasiswa"
      c.font = _fw2(11); c.fill = blue_fill
      c.alignment = Alignment(horizontal="left", vertical="center")
      ws2.row_dimensions[1].height = 18

      ws2.merge_cells("A2:H2")
      c = ws2["A2"]
      c.value = f"{pam_no}  \xb7  {data.get('pt','')}  \xb7  {_fmt_date(data.get('pam_date',''))}"
      c.font = Font(size=8, color="CBD5E1", name="Arial"); c.fill = blue_fill
      c.alignment = Alignment(horizontal="left", vertical="center")

      hdr = ["No","Nama Siswa","Bank","No. Rekening","Atas Nama","Kategori","Kode","Amount (Rp)"]
      for ci, h in enumerate(hdr, 1):
          cell = ws2.cell(3, ci, h)
          cell.font = _fw2(9); cell.fill = blue_fill
          cell.alignment = Alignment(horizontal="center", vertical="center")
          cell.border = _bdr2

      total = 0.0
      for i, pb in enumerate(payments, 1):
          r   = 3 + i
          cat = f"{pb.get('cat1','')}/{pb.get('cat2','')}"
          row_data = [i, pb.get("nama") or pb.get("siswa_code",""),
                      pb.get("bank") or "", pb.get("norek") or "",
                      pb.get("namarek") or "", cat,
                      pb.get("siswa_code",""), float(pb.get("amount",0))]
          fill = white_fill if i % 2 else lgray_fill
          for ci, v in enumerate(row_data, 1):
              cell = ws2.cell(r, ci, v)
              cell.font = _fn2(9); cell.fill = fill
              cell.alignment = Alignment(
                  horizontal="center" if ci in (1,3) else ("right" if ci==8 else "left"),
                  vertical="center")
              cell.border = _bdr2
              if ci == 8:
                  cell.number_format = '#,##0'
          total += float(pb.get("amount", 0))

      tr  = 3 + len(payments) + 1
      tc7 = ws2.cell(tr, 7, "TOTAL")
      tc7.font = _fb2(9)
      tc7.fill = PatternFill("solid", fgColor="E8F0FE")
      tc7.alignment = Alignment(horizontal="right", vertical="center")
      tc7.border = _bdr2
      tc8 = ws2.cell(tr, 8, total)
      tc8.font = _fb2(9)
      tc8.fill = PatternFill("solid", fgColor="E8F0FE")
      tc8.alignment = Alignment(horizontal="right", vertical="center")
      tc8.number_format = '#,##0'
      tc8.border = _bdr2

      for col, w in zip("ABCDEFGH", [5,22,12,16,18,18,10,14]):
          ws2.column_dimensions[col].width = w

      buf = io.BytesIO()
      wb.save(buf)
      buf.seek(0)
      return buf.read()
  ```

- [ ] **Step 4: Run tests**

  ```
  python -m pytest tests/test_pam_exports.py::test_export_pam_excel_custom_returns_xlsx tests/test_pam_exports.py::test_export_pam_excel_custom_has_two_sheets tests/test_pam_exports.py::test_export_pam_excel_custom_pam_no_in_sheet tests/test_pam_exports.py::test_export_pam_excel_custom_approved_by_in_sheet -v
  ```
  Expected: all 4 PASS

- [ ] **Step 5: Run full suite**

  ```
  python -m pytest tests/ -q --tb=short
  ```
  Expected: all previously-passing tests still pass.

- [ ] **Step 6: Commit**

  ```
  git add modules/payment_memo/exports.py tests/test_pam_exports.py
  git commit -m "feat(pam): add export_pam_excel_custom() from user-supplied data"
  ```

---

## Task 4 — Add POST routes for custom PDF and Excel export

**Files:**
- Modify: `modules/payment_memo/routes.py` (append two routes + update imports)
- Test: `tests/test_memo_api.py`

- [ ] **Step 1: Write failing tests**

  Add to `tests/test_memo_api.py`:

  ```python
  _CUSTOM_PAYLOAD = {
      "pam_no": "PAM-001-ETF-05-2026",
      "pam_date": "2026-05-26",
      "requestors_name": "Jany Turkanda",
      "department": "HR",
      "cost_center": "1008C1POFF",
      "gl_account": "70110230",
      "so_sc": "",
      "pt": "PT. SMART Tbk",
      "bu_upstream": False, "bu_downstream": False, "bu_corporate": True,
      "type_downpayment": False, "type_invoice": True, "type_advance": False,
      "vendor_name": "Terlampir",
      "invoice_memo_no": "-",
      "total_amount": 5000000,
      "due_date": "2026-06-26",
      "bank_account_name": "Terlampir",
      "bank_name": "Terlampir",
      "bank_account_no": "Terlampir",
      "approved_by_1": "Hong Tjhin",
      "approved_by_2": "Tenti Kidjo",
  }


  def _seed_pam_for_custom(conn):
      from modules.payment_memo.service import create_pam_record
      pam_no = create_pam_record(conn, 2, "ETF", {
          "pam_date": "2026-05-26", "pt": "PT. SMART Tbk",
          "keterangan": "Test", "total_amount": 5000000.0, "payment_ids": [],
      })
      conn.commit()
      pam_id = conn.execute(
          "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
      ).fetchone()["id"]
      return pam_id


  def test_export_pam_pdf_custom_route_returns_pdf(client):
      from database import get_conn
      conn = get_conn()
      try:
          pam_id = _seed_pam_for_custom(conn)
      finally:
          conn.close()

      token = _login(client)
      with client.session_transaction() as sess:
          sess["company_id"] = 2
      rv = client.post(f"/payment-memo/pam/{pam_id}/export/pdf-custom",
                       json=_CUSTOM_PAYLOAD,
                       headers={"Authorization": f"Bearer {token}"})
      assert rv.status_code == 200
      assert rv.content_type == "application/pdf"
      assert rv.data[:4] == b'%PDF'


  def test_export_pam_excel_custom_route_returns_xlsx(client):
      import zipfile, io as _io
      from database import get_conn
      conn = get_conn()
      try:
          pam_id = _seed_pam_for_custom(conn)
      finally:
          conn.close()

      token = _login(client)
      with client.session_transaction() as sess:
          sess["company_id"] = 2
      rv = client.post(f"/payment-memo/pam/{pam_id}/export/excel-custom",
                       json=_CUSTOM_PAYLOAD,
                       headers={"Authorization": f"Bearer {token}"})
      assert rv.status_code == 200
      assert "spreadsheetml" in rv.content_type
      assert zipfile.is_zipfile(_io.BytesIO(rv.data))
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  ```
  python -m pytest tests/test_memo_api.py::test_export_pam_pdf_custom_route_returns_pdf -v
  ```
  Expected: FAIL — 404 (route not found)

- [ ] **Step 3: Update imports in `routes.py`**

  Find the existing imports line:
  ```python
  from modules.payment_memo.exports import export_pam_pdf, export_pam_excel
  ```

  Replace with:
  ```python
  from modules.payment_memo.exports import (
      export_pam_pdf, export_pam_excel,
      export_pam_pdf_custom, export_pam_excel_custom,
  )
  ```

- [ ] **Step 4: Append two new routes to `routes.py`**

  Add at the end of the file (after the `update_gl_account` route):

  ```python
  @bp.route("/pam/<int:pam_id>/export/pdf-custom", methods=["POST"])
  @role_required("requester", "verificator", "releaser")
  def export_pam_pdf_custom_route(pam_id):
      data       = request.get_json(force=True) or {}
      company_id = session.get("company_id", 0)
      pam_no     = (data.get("pam_no") or "").strip()
      payments   = get_pam_payments(pam_no, company_id)
      pdf_bytes  = export_pam_pdf_custom(data, payments)
      fname      = f"{pam_no or f'pam_{pam_id}'}.pdf"
      return send_file(
          io.BytesIO(pdf_bytes),
          mimetype="application/pdf",
          download_name=fname,
          as_attachment=True,
      )


  @bp.route("/pam/<int:pam_id>/export/excel-custom", methods=["POST"])
  @role_required("requester", "verificator", "releaser")
  def export_pam_excel_custom_route(pam_id):
      data       = request.get_json(force=True) or {}
      company_id = session.get("company_id", 0)
      pam_no     = (data.get("pam_no") or "").strip()
      payments   = get_pam_payments(pam_no, company_id)
      xls_bytes  = export_pam_excel_custom(data, payments)
      fname      = f"{pam_no or f'pam_{pam_id}'}.xlsx"
      return send_file(
          io.BytesIO(xls_bytes),
          mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          download_name=fname,
          as_attachment=True,
      )
  ```

- [ ] **Step 5: Run tests**

  ```
  python -m pytest tests/test_memo_api.py::test_export_pam_pdf_custom_route_returns_pdf tests/test_memo_api.py::test_export_pam_excel_custom_route_returns_xlsx -v
  ```
  Expected: both PASS

- [ ] **Step 6: Run full suite**

  ```
  python -m pytest tests/ -q --tb=short
  ```
  Expected: all previously-passing tests still pass.

- [ ] **Step 7: Commit**

  ```
  git add modules/payment_memo/routes.py tests/test_memo_api.py
  git commit -m "feat(pam): POST routes for pdf-custom and excel-custom export"
  ```

---

## Task 5 — Rewrite `dmRenderForm()` with inline editable inputs

**Files:**
- Modify: `templates/payment_memo/index.html`

No automated tests for this task — manual browser verification described in Step 4.

- [ ] **Step 1: Remove `#dm-approved-bar` from the Draft Memo tab HTML**

  In the `tab-draft-memo` div (around line 183–188), find and **remove** this entire block:
  ```html
  <div id="dm-approved-bar" style="display:none;align-items:center;gap:8px;flex-wrap:wrap">
    <label style="font-size:12px;font-weight:600;color:#374151">Approved by:</label>
    <input id="dm-ab1" type="text" style="border:1px solid #d1d5db;border-radius:4px;padding:4px 8px;font-size:12px;width:130px">
    <input id="dm-ab2" type="text" style="border:1px solid #d1d5db;border-radius:4px;padding:4px 8px;font-size:12px;width:130px">
    <span style="font-size:11px;color:#94a3b8">(dari config, bisa diubah)</span>
  </div>
  ```

- [ ] **Step 2: Replace `dmRenderForm()` in the `<script>` block**

  Find the entire `dmRenderForm` function (lines ~783–876) and replace it with:

  ```javascript
  function dmRenderForm(p) {
    const inp = (id, val, type, extra) => {
      type  = type  || 'text';
      extra = extra || '';
      const v = (val === null || val === undefined) ? '' : val;
      return `<input class="dm-inp" type="${type}" id="${id}" value="${esc(String(v))}" ${extra}>`;
    };

    const field = (lbl, inputHtml) =>
      `<div style="display:flex;align-items:stretch;border-bottom:1px solid #f1f5f9">
        <div style="background:#f8fafc;padding:5px 8px;font-weight:700;font-size:11px;color:#374151;min-width:140px;border-right:1px solid #e2e8f0;display:flex;align-items:center">${esc(lbl)}</div>
        <div style="padding:4px 8px;font-size:11px;color:#1e293b;flex:1;display:flex;align-items:center">
          <span style="color:#94a3b8;margin-right:4px">:</span>${inputHtml}
        </div>
      </div>`;

    const sectionH = t =>
      `<div style="background:#e2e8f0;padding:4px 8px;font-weight:700;font-size:10px;color:#374151;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid #d1d5db">${t}</div>`;

    const cbRow = (id, label, checked) =>
      `<div style="padding:4px 8px;font-size:11px;background:#fffbeb;border-bottom:1px solid #f1f5f9;display:flex;align-items:center">
        <input type="checkbox" id="${id}" class="dm-cb" ${checked ? 'checked' : ''}>
        <label for="${id}" style="cursor:pointer;margin-left:4px">${label}</label>
      </div>`;

    const dateVal = s => (s || '').slice(0, 10);

    return `
    <style>
      .dm-inp{border:none;border-bottom:1px dashed #94a3b8;background:transparent;font-size:11px;font-family:Arial,sans-serif;padding:1px 2px;outline:none;width:100%;box-sizing:border-box;color:#1e293b}
      .dm-inp:focus{border-bottom:1.5px solid #3b82f6;background:#eff6ff;border-radius:2px}
      .dm-inp[type=number]{text-align:right}
      .dm-inp[type=date]{font-size:10px}
      .dm-cb{width:14px;height:14px;cursor:pointer;accent-color:#1e3a5f;flex-shrink:0}
    </style>
    <div style="border:1px solid #94a3b8;border-radius:4px;overflow:hidden;font-family:Arial,sans-serif;max-width:860px">
      <div style="background:#1e3a5f;color:#fff;text-align:center;font-size:14px;font-weight:900;padding:10px;letter-spacing:2px;border-bottom:3px solid #f59e0b">PAYMENT APPROVAL MEMO</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;border-bottom:1px solid #e2e8f0">
        <div style="border-right:1px solid #e2e8f0">
          ${field('PAM No.', inp('dm-f-pam-no', p.pam_no))}
          ${field('Date', inp('dm-f-date', dateVal(p.pam_date), 'date'))}
          ${field("Requestor's Name", inp('dm-f-requestor', p.requestors_name))}
          ${field('Department', inp('dm-f-dept', '-'))}
        </div>
        <div>
          ${field('Cost Center', inp('dm-f-cc', p.cost_center))}
          ${field('GL Account', inp('dm-f-gl', p.gl_account))}
          ${field('SO / SC', inp('dm-f-sosc', ''))}
          ${field('Company', inp('dm-f-company', p.pt))}
        </div>
      </div>
      ${sectionH('Business Unit')}
      <div style="padding:5px 8px;font-size:11px;background:#fffbeb;border-bottom:1px solid #f1f5f9;display:flex;gap:20px;align-items:center">
        <label style="display:flex;align-items:center;gap:4px;cursor:pointer"><input type="checkbox" id="dm-f-bu-upstream"   class="dm-cb"> Upstream</label>
        <label style="display:flex;align-items:center;gap:4px;cursor:pointer"><input type="checkbox" id="dm-f-bu-downstream" class="dm-cb"> Downstream</label>
        <label style="display:flex;align-items:center;gap:4px;cursor:pointer"><input type="checkbox" id="dm-f-bu-corporate"  class="dm-cb" checked> Corporate</label>
      </div>
      ${sectionH('Type of Request')}
      ${cbRow('dm-f-type-dp',  'Downpayment to vendor', false)}
      ${cbRow('dm-f-type-inv', 'Invoice Payment – Non PO Invoice', true)}
      ${cbRow('dm-f-type-adv', 'Employee Advance / Reimbursement (Fund Transfer)', false)}
      ${sectionH('Invoice Information')}
      <div style="display:grid;grid-template-columns:1fr 1fr;border-bottom:1px solid #e2e8f0">
        <div style="border-right:1px solid #e2e8f0">
          ${field('Vendor Name', inp('dm-f-vendor', 'Terlampir'))}
          ${field('Invoice Amount', inp('dm-f-amount', p.total_amount || 0, 'number', 'step="1" min="0"'))}
        </div>
        <div>
          ${field('Invoice / Memo No', inp('dm-f-inv-no', '-'))}
          ${field('Expected Due Date', inp('dm-f-due', dateVal(p.due_date), 'date'))}
        </div>
      </div>
      ${sectionH('Vendor Bank Account Details')}
      ${field('Bank Account Name',   inp('dm-f-bank-name', 'Terlampir'))}
      ${field('Bank Name',           inp('dm-f-bank',      'Terlampir'))}
      ${field('Bank Account Number', inp('dm-f-bank-no',   'Terlampir'))}
      <div style="display:grid;grid-template-columns:1fr 1fr;border-top:1px solid #e2e8f0">
        <div style="padding:8px 10px;border-right:1px solid #e2e8f0">
          <div style="font-size:10px;font-weight:700;color:#374151;background:#f8fafc;padding:3px 5px;margin-bottom:6px">Request by</div>
          ${inp('dm-f-requestor-sig', p.requestors_name)}
        </div>
        <div style="padding:8px 10px">
          <div style="font-size:10px;font-weight:700;color:#374151;background:#f8fafc;padding:3px 5px;margin-bottom:6px">Approved by</div>
          <div style="display:flex;gap:8px">
            ${inp('dm-f-ab1', PAM_APPROVED_BY_1)}
            ${inp('dm-f-ab2', PAM_APPROVED_BY_2)}
          </div>
        </div>
      </div>
      <div style="padding:6px 10px;font-weight:700;font-size:10px;color:#374151;background:#f8fafc;border-top:1px solid #e2e8f0">Checked by (QA)</div>
      <div style="height:36px;border-top:1px solid #e2e8f0"></div>
    </div>`;
  }
  ```

- [ ] **Step 3: Remove the old footer note and `_dmExportUrl()` function**

  Find and remove this block (around line 872–874 in the form preview):
  ```html
  <div style="padding:4px 8px;font-size:10px;color:#94a3b8;font-style:italic;border-top:1px solid #f1f5f9">
    &#9658; Lampiran jadwal siswa: halaman 2 di PDF / sheet &#34;Lampiran&#34; di Excel
  </div>
  ```

  Find and remove the entire `_dmExportUrl()` function in the `<script>` block:
  ```javascript
  function _dmExportUrl(format) {
    if (!_dmPamId) { showToast('Pilih PAM No terlebih dahulu.', 'error'); return null; }
    const ab1 = encodeURIComponent(document.getElementById('dm-ab1').value || '');
    const ab2 = encodeURIComponent(document.getElementById('dm-ab2').value || '');
    return `/payment-memo/pam/${_dmPamId}/export/${format}?approved_by_1=${ab1}&approved_by_2=${ab2}`;
  }
  ```

- [ ] **Step 4: Manual browser verification**

  Start the server:
  ```
  python run.py
  ```
  1. Navigate to `/payment-memo/` and open the **Draft Memo** tab.
  2. Type a PAM No in the search box and select a result.
  3. Confirm the form renders with all fields showing thin dashed underlines.
  4. Click the Date field — a date picker should open.
  5. Click the Invoice Amount field — verify it accepts number input.
  6. Click a checkbox — verify it toggles checked/unchecked state.
  7. Verify the "Approved by" and "Request by" sections show inline inputs inside the form (not above it).

- [ ] **Step 5: Commit**

  ```
  git add templates/payment_memo/index.html
  git commit -m "feat(pam): rewrite dmRenderForm with inline editable inputs"
  ```

---

## Task 6 — Add `collectDmFields()` and POST blob-download exports

**Files:**
- Modify: `templates/payment_memo/index.html`

- [ ] **Step 1: Add state variables and `collectDmFields()` in the `<script>` block**

  Find these lines near the top of the Draft Memo JS section (around line 734):
  ```javascript
  let _dmPamId = null;
  let _dmSearchTimer = null;
  ```

  Replace with:
  ```javascript
  let _dmPamId = null;
  let _dmSearchTimer = null;
  let _dmPayments = [];
  let _dmLampiranOpen = false;
  ```

  After those lines, add:
  ```javascript
  function collectDmFields() {
    const g = id => document.getElementById(id);
    return {
      pam_no:            g('dm-f-pam-no').value.trim(),
      pam_date:          g('dm-f-date').value,
      requestors_name:   g('dm-f-requestor').value.trim(),
      department:        g('dm-f-dept').value.trim(),
      cost_center:       g('dm-f-cc').value.trim(),
      gl_account:        g('dm-f-gl').value.trim(),
      so_sc:             g('dm-f-sosc').value.trim(),
      pt:                g('dm-f-company').value.trim(),
      bu_upstream:       g('dm-f-bu-upstream').checked,
      bu_downstream:     g('dm-f-bu-downstream').checked,
      bu_corporate:      g('dm-f-bu-corporate').checked,
      type_downpayment:  g('dm-f-type-dp').checked,
      type_invoice:      g('dm-f-type-inv').checked,
      type_advance:      g('dm-f-type-adv').checked,
      vendor_name:       g('dm-f-vendor').value.trim(),
      invoice_memo_no:   g('dm-f-inv-no').value.trim(),
      total_amount:      parseFloat(g('dm-f-amount').value) || 0,
      due_date:          g('dm-f-due').value,
      bank_account_name: g('dm-f-bank-name').value.trim(),
      bank_name:         g('dm-f-bank').value.trim(),
      bank_account_no:   g('dm-f-bank-no').value.trim(),
      approved_by_1:     g('dm-f-ab1').value.trim(),
      approved_by_2:     g('dm-f-ab2').value.trim(),
    };
  }
  ```

- [ ] **Step 2: Replace `dmExportPDF()` and `dmExportExcel()`**

  Find the existing functions:
  ```javascript
  function dmExportPDF() {
    const url = _dmExportUrl('pdf');
    if (url) window.open(url, '_blank');
  }

  function dmExportExcel() {
    const url = _dmExportUrl('excel');
    if (url) window.open(url, '_blank');
  }
  ```

  Replace with:
  ```javascript
  async function dmExportPDF() {
    if (!_dmPamId) { showToast('Pilih PAM No terlebih dahulu.', 'error'); return; }
    const payload = collectDmFields();
    const resp = await apiFetch(`/payment-memo/pam/${_dmPamId}/export/pdf-custom`, {
      method: 'POST', body: JSON.stringify(payload),
    });
    if (!resp) return;
    const blob = await resp.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${payload.pam_no || 'PAM'}.pdf`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function dmExportExcel() {
    if (!_dmPamId) { showToast('Pilih PAM No terlebih dahulu.', 'error'); return; }
    const payload = collectDmFields();
    const resp = await apiFetch(`/payment-memo/pam/${_dmPamId}/export/excel-custom`, {
      method: 'POST', body: JSON.stringify(payload),
    });
    if (!resp) return;
    const blob = await resp.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${payload.pam_no || 'PAM'}.xlsx`;
    a.click();
    URL.revokeObjectURL(a.href);
  }
  ```

- [ ] **Step 3: Update `dmSelectPAM()` to remove old approved-bar wiring**

  Find the current `dmSelectPAM()` (around line 761–781):
  ```javascript
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
  ```

  Replace with:
  ```javascript
  async function dmSelectPAM(pamId, pamNo) {
    document.getElementById('dm-pam-search').value = pamNo;
    document.getElementById('dm-pam-dropdown').style.display = 'none';
    _dmPamId = pamId;

    const resp = await apiFetch(`/payment-memo/pam/${pamId}/detail`);
    const data = await resp.json();
    if (!data.ok) { showToast('Gagal memuat PAM detail.', 'error'); return; }

    const p = data.data;
    _dmPayments = p.payments || [];
    _dmLampiranOpen = false;

    document.getElementById('dm-export-btns').style.display = 'flex';
    document.getElementById('dm-form-preview').innerHTML = dmRenderForm(p);

    const lampWrap = document.getElementById('dm-lampiran-wrap');
    if (lampWrap) {
      lampWrap.style.display = 'block';
      document.getElementById('dm-lampiran-body').style.display = 'none';
      document.getElementById('dm-lampiran-toggle').textContent =
        `▶ Lampiran — Jadwal Pembayaran (${_dmPayments.length} siswa)`;
    }
  }
  ```

- [ ] **Step 4: Manual browser verification**

  With server running:
  1. Select a PAM from the dropdown.
  2. Edit any field (e.g., change Department to "Finance").
  3. Click **PDF** — verify the download starts and the PDF contains "Finance" in the Department row.
  4. Click **Excel** — verify the `.xlsx` download starts.
  5. Check the Excel Sheet 1 contains the edited Department value.

- [ ] **Step 5: Commit**

  ```
  git add templates/payment_memo/index.html
  git commit -m "feat(pam): collectDmFields + POST blob export for Draft Memo"
  ```

---

## Task 7 — Add Lampiran collapsible section

**Files:**
- Modify: `templates/payment_memo/index.html`

- [ ] **Step 1: Add `#dm-lampiran-wrap` HTML after `#dm-form-preview`**

  Find in the `tab-draft-memo` div:
  ```html
  <div id="dm-form-preview"></div>
  ```

  Replace with:
  ```html
  <div id="dm-form-preview"></div>
  <div id="dm-lampiran-wrap" style="display:none;margin-top:12px;max-width:860px">
    <button id="dm-lampiran-toggle" onclick="toggleLampiran()"
      style="background:#1e3a5f;color:#fff;border:none;border-radius:5px;padding:7px 16px;font-size:12px;font-weight:700;cursor:pointer;width:100%;text-align:left;letter-spacing:.3px">
      &#x25b6; Lampiran &mdash; Jadwal Pembayaran
    </button>
    <div id="dm-lampiran-body" style="display:none;margin-top:4px;border:1px solid #e2e8f0;border-radius:4px;overflow:hidden"></div>
  </div>
  ```

- [ ] **Step 2: Add `toggleLampiran()` and `dmRenderLampiran()` to the `<script>` block**

  After the `dmExportExcel()` function, add:

  ```javascript
  function toggleLampiran() {
    _dmLampiranOpen = !_dmLampiranOpen;
    const body   = document.getElementById('dm-lampiran-body');
    const toggle = document.getElementById('dm-lampiran-toggle');
    if (_dmLampiranOpen) {
      body.innerHTML = dmRenderLampiran(_dmPayments);
      body.style.display = 'block';
      toggle.textContent = toggle.textContent.replace('▶', '▼');
    } else {
      body.style.display = 'none';
      toggle.textContent = toggle.textContent.replace('▼', '▶');
    }
  }

  function dmRenderLampiran(payments) {
    if (!payments || !payments.length)
      return '<div style="padding:16px;text-align:center;color:#6b7280;font-size:12px">Tidak ada data pembayaran dalam PAM ini.</div>';

    const hdrs = ['No','Nama Siswa','Bank','No. Rekening','Atas Nama','Kategori','Kode','Amount (Rp)'];
    const thRow = hdrs.map((h, i) =>
      `<th style="padding:7px 8px;background:#1e3a5f;color:#fff;font-size:11px;font-weight:700;text-align:${i===7?'right':'left'};white-space:nowrap">${h}</th>`
    ).join('');

    let total = 0;
    const rows = payments.map((pb, i) => {
      const amt = parseFloat(pb.amount || 0);
      total += amt;
      const cat = `${pb.cat1 || ''}/${pb.cat2 || ''}`;
      const bg = i % 2 === 0 ? '#fff' : '#f8fafc';
      return `<tr style="background:${bg}">
        <td style="padding:6px 8px;text-align:center;font-size:11px">${i+1}</td>
        <td style="padding:6px 8px;font-size:11px">${esc(pb.nama || pb.siswa_code || '')}</td>
        <td style="padding:6px 8px;font-size:11px">${esc(pb.bank || '')}</td>
        <td style="padding:6px 8px;font-size:11px;font-family:monospace">${esc(pb.norek || '')}</td>
        <td style="padding:6px 8px;font-size:11px">${esc(pb.namarek || '')}</td>
        <td style="padding:6px 8px;font-size:11px">${esc(cat)}</td>
        <td style="padding:6px 8px;font-size:11px;font-family:monospace">${esc(pb.siswa_code || '')}</td>
        <td style="padding:6px 8px;font-size:11px;text-align:right">${fmtRupiah(amt)}</td>
      </tr>`;
    }).join('');

    return `<table style="width:100%;border-collapse:collapse">
      <thead><tr>${thRow}</tr></thead>
      <tbody>${rows}</tbody>
      <tfoot>
        <tr style="background:#e8f0fe;font-weight:700">
          <td colspan="7" style="padding:6px 8px;font-size:11px;text-align:right">TOTAL</td>
          <td style="padding:6px 8px;font-size:11px;text-align:right">${fmtRupiah(total)}</td>
        </tr>
      </tfoot>
    </table>`;
  }
  ```

- [ ] **Step 3: Manual browser verification**

  With server running:
  1. Select a PAM that has payment records.
  2. Confirm the **▶ Lampiran — Jadwal Pembayaran (N siswa)** button appears below the form.
  3. Click the button — table expands with the student payment rows and a TOTAL footer.
  4. Click again — table collapses.
  5. Select a PAM with zero payments — button shows **(0 siswa)**, clicking shows the empty message.

- [ ] **Step 4: Run full test suite one final time**

  ```
  python -m pytest tests/ -q --tb=short
  ```
  Expected: all previously-passing tests still pass, new tests from Tasks 1–4 pass (≥ 66 passing total).

- [ ] **Step 5: Commit**

  ```
  git add templates/payment_memo/index.html
  git commit -m "feat(pam): collapsible Lampiran section in Draft Memo tab"
  ```
