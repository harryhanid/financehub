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
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from modules.payment_memo.service import get_pam_detail, get_pam_payments

_BLUE   = colors.HexColor("#1e3a5f")
_GOLD   = colors.HexColor("#f59e0b")
_GRAY   = colors.HexColor("#e2e8f0")
_LGRAY  = colors.HexColor("#f8fafc")
_WHITE  = colors.white
_AMBER  = colors.HexColor("#fffbeb")


def _fmt_date(s: str) -> str:
    try:
        dt = datetime.strptime(s[:10], "%Y-%m-%d")
        return dt.strftime("%d %B %Y").lstrip("0")
    except Exception:
        return s or ""


def _fmt_rp(v) -> str:
    try:
        return f"Rp {float(v):,.0f}"
    except Exception:
        return str(v)


def _style(name, **kw):
    defaults = {"fontName": "Helvetica", "fontSize": 8, "leading": 10}
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)


_S_LABEL   = _style("lbl",  fontName="Helvetica-Bold", fontSize=8,
                     textColor=colors.HexColor("#374151"))
_S_VAL     = _style("val",  fontSize=8.5, textColor=colors.HexColor("#1e293b"))
_S_VAL_HI  = _style("valhi", fontName="Helvetica-Bold", fontSize=9,
                     textColor=colors.HexColor("#1e3a5f"))
_S_SECTION = _style("sec",  fontName="Helvetica-Bold", fontSize=7.5,
                     textColor=colors.HexColor("#374151"))
_S_CB      = _style("cb",   fontSize=8, textColor=colors.HexColor("#1e293b"))
_S_TITLE   = _style("ttl",  fontName="Helvetica-Bold", fontSize=13,
                     alignment=TA_CENTER, textColor=_WHITE)
_S_ATCH_H  = _style("atch", fontName="Helvetica-Bold", fontSize=9, textColor=_WHITE)
_S_TH      = _style("th",   fontName="Helvetica-Bold", fontSize=8,
                     textColor=_WHITE, alignment=TA_CENTER)
_S_TD      = _style("td",   fontSize=8, textColor=colors.HexColor("#1e293b"))
_S_TD_R    = _style("tdr",  fontSize=8, alignment=2,
                     textColor=colors.HexColor("#1e293b"))

_CW = [3.8*cm, 4.7*cm, 3.8*cm, 4.7*cm]


def _p(s, style=None):
    return Paragraph(str(s) if s is not None else "", style or _S_VAL)


def _terlampir():
    return _p("Terlampir", _style("tl", fontName="Helvetica-Bold",
                                  fontSize=8, textColor=colors.HexColor("#92400e"),
                                  backColor=colors.HexColor("#fef3c7")))


def _build_pam_table(pam: dict, approved_by_1: str, approved_by_2: str) -> Table:
    pam_date    = _fmt_date(pam.get("pam_date", ""))
    due_date    = _fmt_date(pam.get("due_date", ""))
    invoice_amt = _fmt_rp(pam.get("total_amount", 0))

    data = [
        [_p("PAM No.", _S_LABEL), _p(pam.get("pam_no", ""), _S_VAL_HI),
         _p("Cost Center", _S_LABEL), _p(pam.get("cost_center", ""), _S_VAL)],
        [_p("Date", _S_LABEL), _p(pam_date, _S_VAL),
         _p("GL Account", _S_LABEL), _p(str(pam.get("gl_account", "")), _S_VAL)],
        [_p("Requestor's Name", _S_LABEL), _p(pam.get("requestors_name", ""), _S_VAL),
         _p("SO / SC", _S_LABEL), _p("", _S_VAL)],
        [_p("Department", _S_LABEL), _p("-", _S_VAL),
         _p("Company", _S_LABEL), _p(pam.get("pt", ""), _S_VAL)],
        [_p("Business Unit", _S_SECTION), "", "", ""],
        [_p("☐  Upstream          ☐  Downstream          ☑  Corporate", _S_CB),
         "", "", ""],
        [_p("Type of Request", _S_SECTION), "", "", ""],
        [_p("☐  Downpayment to vendor", _S_CB), "", "", ""],
        [_p("☑  Invoice Payment – Non PO Invoice", _S_CB), "", "", ""],
        [_p("☐  Employee Advance / Reimbursement (Fund Transfer)", _S_CB), "", "", ""],
        [_p("Invoice Information", _S_SECTION), "", "", ""],
        [_p("Vendor Name", _S_LABEL), _terlampir(),
         _p("Invoice / Memo No", _S_LABEL), _p("-", _S_VAL)],
        [_p("Invoice Amount", _S_LABEL), _p(invoice_amt, _S_VAL_HI),
         _p("Expected Due Date", _S_LABEL), _p(due_date, _S_VAL)],
        [_p("Vendor Bank Account Details", _S_SECTION), "", "", ""],
        [_p("Bank Account Name", _S_LABEL),  _terlampir(), "", ""],
        [_p("Bank Name", _S_LABEL),          _terlampir(), "", ""],
        [_p("Bank Account Number", _S_LABEL), _terlampir(), "", ""],
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

    return Table(data, colWidths=_CW, style=TableStyle(style_cmds))


def _build_signature_table(requestors_name: str,
                           approved_by_1: str,
                           approved_by_2: str) -> Table:
    data = [
        [_p("Request by", _S_LABEL),  "", _p("Approved by", _S_LABEL), ""],
        ["", "", "", ""],
        ["", "", "", ""],
        ["", "", "", ""],
        [_p(requestors_name, _style("sn", fontName="Helvetica-Bold", fontSize=8)),
         "",
         _p(f"{approved_by_1}          {approved_by_2}",
            _style("sn2", fontName="Helvetica-Bold", fontSize=8)),
         ""],
        [_p("Checked by (QA)", _S_LABEL), "", "", ""],
        ["", "", "", ""],
        ["", "", "", ""],
        ["", "", "", ""],
    ]
    cw = [4.25*cm, 4.25*cm, 4.25*cm, 4.25*cm]
    style_cmds = [
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("BACKGROUND",    (0, 0), (-1, -1), _LGRAY),
        ("SPAN", (0, 0), (1, 0)), ("SPAN", (0, 1), (1, 1)),
        ("SPAN", (0, 2), (1, 2)), ("SPAN", (0, 3), (1, 3)),
        ("SPAN", (0, 4), (1, 4)),
        ("SPAN", (2, 0), (3, 0)), ("SPAN", (2, 1), (3, 1)),
        ("SPAN", (2, 2), (3, 2)), ("SPAN", (2, 3), (3, 3)),
        ("SPAN", (2, 4), (3, 4)),
        ("SPAN", (0, 5), (3, 5)), ("SPAN", (0, 6), (3, 6)),
        ("SPAN", (0, 7), (3, 7)), ("SPAN", (0, 8), (3, 8)),
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
    payments      = get_pam_payments(pam_no, company_id)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )
    elems = []

    # Page 1: PAM Form
    title_data = [[_p("PAYMENT APPROVAL MEMO", _S_TITLE)]]
    title_tbl  = Table(title_data, colWidths=[17*cm])
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _BLUE),
        ("LINEBELOW",     (0, 0), (-1, -1), 3, _GOLD),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elems.append(title_tbl)
    elems.append(Spacer(1, 0.15*cm))
    elems.append(_build_pam_table(pam, approved_by_1, approved_by_2))
    elems.append(Spacer(1, 0.3*cm))
    elems.append(_build_signature_table(
        pam.get("requestors_name", ""), approved_by_1, approved_by_2
    ))

    # Page 2: Lampiran
    elems.append(PageBreak())

    att_hdr_tbl = Table(
        [[_p(f"Lampiran — Jadwal Pembayaran Beasiswa", _S_ATCH_H)],
         [_p(f"{pam_no}  ·  {pam.get('pt','')}  ·  {_fmt_date(pam.get('pam_date',''))}",
             _style("atsub", fontSize=7.5, textColor=colors.HexColor("#cbd5e1")))]],
        colWidths=[17*cm]
    )
    att_hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _BLUE),
        ("LINEBELOW",     (0, -1), (-1, -1), 3, _GOLD),
        ("TOPPADDING",    (0, 0), (0, 0), 7),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    elems.append(att_hdr_tbl)
    elems.append(Spacer(1, 0.3*cm))

    headers = ["No", "Nama Siswa", "Bank", "No. Rekening",
               "Atas Nama", "Kategori", "Kode", "Amount (Rp)"]
    rows = [[_p(h, _S_TH) for h in headers]]
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


# ─────────────────────────────────────────────────────────────────────────────
# Excel export — Book6.xlsx standard format
# ─────────────────────────────────────────────────────────────────────────────

def export_pam_excel(pam_id: int, company_id: int,
                     approved_by_1: str, approved_by_2: str) -> bytes:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from datetime import datetime as _dt

    pam = get_pam_detail(pam_id, company_id)
    if not pam:
        raise ValueError("PAM record tidak ditemukan.")

    approved_by_1 = approved_by_1 or config.PAM_APPROVED_BY_1
    approved_by_2 = approved_by_2 or config.PAM_APPROVED_BY_2
    pam_no        = pam["pam_no"]
    payments      = get_pam_payments(pam_no, company_id)

    wb = openpyxl.Workbook()

    # ── Sheet 1: PAM NEW (Book6 standard format — no fills, exact layout) ────
    ws = wb.active
    ws.title = "PAM NEW"

    # Column widths from Book6
    for col, w in [("A",3.0),("B",11.15),("C",1.84),("D",7.53),("E",2.15),
                   ("F",2.84),("G",9.0),("H",2.0),("J",4.53),("K",5.69),
                   ("L",4.69),("N",5.30),("O",1.15),("P",7.84)]:
        ws.column_dimensions[col].width = w

    # Row heights from Book6
    ws.row_dimensions[9].height  = 8.25
    ws.row_dimensions[11].height = 16.5
    ws.row_dimensions[12].height = 11.25
    ws.row_dimensions[19].height = 17.25
    ws.row_dimensions[25].height = 15.0

    _thin      = Side(style="thin")
    _box       = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)
    _box_lr    = Border(left=_thin, top=_thin, bottom=_thin)  # no right (B42/G42)
    _C         = Alignment(horizontal="center", vertical="center", wrap_text=True)
    _L         = Alignment(horizontal="left",   vertical="center")
    _R         = Alignment(horizontal="right",  vertical="center")

    def _bold(sz=11): return Font(bold=True,  size=sz)
    def _norm(sz=11): return Font(bold=False, size=sz)

    def _set(coord, val, font=None, align=None, border=None):
        c = ws[coord]
        c.value = val
        if font:   c.font      = font
        if align:  c.alignment = align
        if border: c.border    = border

    def _draw_box(r1, c1, r2, c2):
        """Draw a thin outline border on all cells of range (r1,c1):(r2,c2)."""
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

    pam_date = _dt_val(pam.get("pam_date", ""))
    due_date = _dt_val(pam.get("due_date", ""))

    # Row 1 — title
    ws.merge_cells("A1:Q1")
    _set("A1", "PAYMENT APPROVAL MEMO", font=_bold(11), align=_C)

    # Row 2 — empty separator
    ws.merge_cells("B2:Q2")

    # Row 4 — PAM No / Cost Center
    ws.merge_cells("L4:N4")
    _set("B4", "PAM No.",                   align=_L)
    _set("E4", ":")
    _set("F4", pam_no,                      align=_L)
    _set("L4", "Cost Center",               align=_R)
    _set("O4", ":",                          align=_R)
    _set("P4", pam.get("cost_center", ""),  align=_L)

    # Row 5 — Date / GL Account
    ws.merge_cells("F5:J5")
    ws.merge_cells("L5:N5")
    ws.merge_cells("P5:Q5")
    _set("B5", "Date",                      align=_L)
    _set("E5", ":")
    _set("F5", pam_date,                    align=_L)
    ws["F5"].number_format = '[$-421]dd\\ mmmm\\ yyyy;@'
    _set("L5", "GL Account",               align=_R)
    _set("O5", ":",                          align=_R)
    _set("P5", pam.get("gl_account", ""),  align=_L)

    # Row 6 — Requestor / SO-SC
    ws.merge_cells("L6:N6")
    _set("B6", "Requestor’s Name   ", align=_L)
    _set("E6", ":")
    _set("F6", pam.get("requestors_name", ""), align=_L)
    _set("L6", "SO / SC",                  align=_R)
    _set("O6", ":",                          align=_R)

    # Row 7 — Department
    _set("B7", "Department",               align=_L)
    _set("E7", ":")
    _set("F7", "-",                         align=_L)

    # Row 8 — Company
    _set("B8", "Company",                  align=_L)
    _set("E8", ":")
    _set("F8", pam.get("pt", ""),          align=_L)

    # Row 10 — Business Unit header
    _set("B10", "Bussiness Unit ",         align=_L)

    # Row 11 — BU checkboxes
    ws.merge_cells("E11:F11")
    ws["E11"].border = _box                         # empty checkbox (Upstream)
    _set("G11", "  Upstream",              align=_L)
    ws["I11"].border = Border(right=_thin)            # shared edge — Downstream checkbox
    ws["J11"].border = Border(top=_thin, bottom=_thin, right=_thin)
    _set("K11", "  Downstream",            align=_L)
    _set("N11", "V",                        align=_C, border=_box)
    _set("O11", "  Corporate",             align=_L)

    # Row 13 — Type of Request header
    _set("B13", "Type of Request ",        align=_L)

    # Row 14 — Downpayment (unchecked)
    ws.merge_cells("E14:F14")
    ws["E14"].border = _box                         # empty checkbox
    _set("G14", "  Downpayment to vendor", align=_L)

    # Row 15 — Invoice Payment (checked)
    ws.merge_cells("E15:F15")
    _set("E15", "V",                        align=_C, border=_box)
    _set("G15", "  Invoice Payment – Non PO Invoice", align=_L)

    # Row 16 — Employee Advance (unchecked)
    ws.merge_cells("E16:F16")
    ws["E16"].border = _box                         # empty checkbox
    _set("G16", "  Employee Advance/ Reimbursement (Fund Transfer)", align=_L)

    # Row 18 — Invoice Information header
    ws.merge_cells("B18:Q18")
    _set("B18", "Invoice Information",     font=_bold(), align=_C)

    # Row 19 — Vendor Name
    ws.merge_cells("I19:Q19")
    _set("G19", "Vendor Name",             align=_R)
    _set("H19", ":",                        align=_R)
    _set("I19", "Terlampir",               align=_L)

    # Row 20 — Invoice/Memo Number
    ws.merge_cells("I20:Q20")
    _set("G20", "Invoice/ Memorandum Number", align=_R)
    _set("H20", ":",                        align=_R)
    _set("I20", "-",                        align=_L)

    # Row 21 — Invoice Amount
    ws.merge_cells("I21:L21")
    _set("G21", "Invoice Amount",          align=_R)
    _set("H21", ":",                        align=_R)
    _set("I21", pam.get("total_amount", 0), align=_C)
    ws["I21"].number_format = '_("Rp"* #,##0_);_("Rp"* \\(#,##0\\);_("Rp"* "-"_);_(@_)'

    # Row 22 — Expected Due Date
    ws.merge_cells("I22:O22")
    _set("G22", "Expected Due Date",       align=_R)
    _set("H22", ":",                        align=_R)
    _set("I22", due_date,                  align=_L)
    ws["I22"].number_format = '[$-421]dd\\ mmmm\\ yyyy;@'

    # Row 24 — Vendor Bank Account header
    ws.merge_cells("B24:Q24")
    _set("B24", "Vendor Bank Account Details", font=_bold(), align=_C)

    # Rows 25-27 — Bank details
    ws.merge_cells("I25:Q25")
    _set("D25", "Bank Account Name ",      align=_L)
    _set("H25", ":")
    _set("I25", "Terlampir",               align=_L)

    ws.merge_cells("I26:Q26")
    _set("D26", "Bank Name ",              align=_L)
    _set("H26", ":")
    _set("I26", "Terlampir",               align=_L)

    ws.merge_cells("I27:Q27")
    _set("D27", "Bank Account Number",     align=_L)
    _set("H27", ":")
    _set("I27", "Terlampir",               align=_L)

    # Row 28 — separator
    ws.merge_cells("I28:Q28")

    # Rows 29-34 — Request by signature
    ws.merge_cells("B29:F29")
    _set("B29", "Request by",              font=_bold(), align=_C, border=_box)
    ws.merge_cells("B30:F33")
    _draw_box(30, 2, 33, 6)   # B30:F33 — Request by signature space
    ws.merge_cells("B34:F34")
    _set("B34", pam.get("requestors_name", ""), align=_C, border=_box)

    # Rows 36-42 — Approved by signature
    ws.merge_cells("B36:K36")
    _set("B36", "Approved by",             font=_bold(), align=_C, border=_box)
    ws.merge_cells("B37:F41")
    _draw_box(37, 2, 41, 6)   # B37:F41 — Approved by left space
    ws.merge_cells("G37:K41")
    _draw_box(37, 7, 41, 11)  # G37:K41 — Approved by right space
    ws.merge_cells("B42:F42")
    ws.merge_cells("G42:K42")
    _set("B42", approved_by_1,             align=_C, border=_box_lr)
    _set("G42", approved_by_2,             align=_C, border=_box_lr)

    # Row 43 — Checked by (QA)
    _set("B43", "Checked by (QA)",         font=_bold())
    ws.merge_cells("B44:F48")
    _draw_box(44, 2, 48, 6)   # B44:F48 — QA signature space

    # ── Sheet 2: Lampiran ────────────────────────────────────────────────────
    ws2 = wb.create_sheet("Lampiran")

    blue_fill  = PatternFill("solid", fgColor="1E3A5F")
    lgray_fill = PatternFill("solid", fgColor="F8FAFC")
    white_fill = PatternFill("solid", fgColor="FFFFFF")
    thin2      = Side(style="thin", color="D1D5DB")
    _bdr2      = Border(left=thin2, right=thin2, top=thin2, bottom=thin2)
    _fw        = lambda sz=9: Font(bold=True, color="FFFFFF", size=sz, name="Arial")
    _fb        = lambda sz=9: Font(bold=True,  size=sz, name="Arial")
    _fn2       = lambda sz=9: Font(bold=False, size=sz, name="Arial")

    ws2.merge_cells("A1:H1")
    c = ws2["A1"]
    c.value = "Lampiran — Jadwal Pembayaran Beasiswa"
    c.font = _fw(11); c.fill = blue_fill
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws2.row_dimensions[1].height = 18

    ws2.merge_cells("A2:H2")
    c = ws2["A2"]
    c.value = f"{pam_no}  ·  {pam.get('pt','')}  ·  {_fmt_date(pam.get('pam_date',''))}"
    c.font = Font(size=8, color="CBD5E1", name="Arial"); c.fill = blue_fill
    c.alignment = Alignment(horizontal="left", vertical="center")

    hdr = ["No","Nama Siswa","Bank","No. Rekening","Atas Nama","Kategori","Kode","Amount (Rp)"]
    for ci, h in enumerate(hdr, 1):
        cell = ws2.cell(3, ci, h)
        cell.font = _fw(9); cell.fill = blue_fill
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

    tr = 3 + len(payments) + 1
    tc7 = ws2.cell(tr, 7, "TOTAL")
    tc7.font = _fb(9)
    tc7.fill = PatternFill("solid", fgColor="E8F0FE")
    tc7.alignment = Alignment(horizontal="right", vertical="center")
    tc7.border = _bdr2
    tc8 = ws2.cell(tr, 8, total)
    tc8.font = _fb(9)
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
