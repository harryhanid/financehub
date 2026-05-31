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
# Excel export
# ─────────────────────────────────────────────────────────────────────────────

def export_pam_excel(pam_id: int, company_id: int,
                     approved_by_1: str, approved_by_2: str) -> bytes:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

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

    thin     = Side(style="thin", color="D1D5DB")
    _border  = Border(left=thin, right=thin, top=thin, bottom=thin)
    _center  = Alignment(horizontal="center", vertical="center", wrap_text=True)
    _left    = Alignment(horizontal="left",   vertical="center", wrap_text=True)

    def _fw(sz=11): return Font(bold=True, color="FFFFFF", size=sz, name="Arial")
    def _fb(sz=9, c="1E293B"): return Font(bold=True,  size=sz, name="Arial", color=c)
    def _fn(sz=9, c="374151"): return Font(bold=False, size=sz, name="Arial", color=c)

    def _s(cell, v, font=None, fill=None, align=None):
        cell.value = v
        if font:  cell.font      = font
        if fill:  cell.fill      = fill
        if align: cell.alignment = align
        cell.border = _border

    # Row 1: Title
    ws1.merge_cells("A1:Q1")
    _s(ws1["A1"], "PAYMENT APPROVAL MEMO", font=_fw(13), fill=blue_fill, align=_center)
    ws1.row_dimensions[1].height = 22

    # Row 2: gold separator
    ws1.merge_cells("A2:Q2")
    ws1["A2"].fill = gold_fill
    ws1.row_dimensions[2].height = 4

    def _field_row(row, lbl_l, val_l, lbl_r, val_r):
        ws1.merge_cells(f"B{row}:D{row}")
        ws1.merge_cells(f"F{row}:J{row}")
        ws1.merge_cells(f"L{row}:N{row}")
        ws1.merge_cells(f"P{row}:Q{row}")
        _s(ws1[f"B{row}"], lbl_l, font=_fb(9,"374151"), fill=lgray_fill, align=_left)
        _s(ws1[f"E{row}"], ":",   font=_fn(), fill=lgray_fill, align=_center)
        _s(ws1[f"F{row}"], val_l, font=_fb(9), fill=white_fill, align=_left)
        _s(ws1[f"L{row}"], lbl_r, font=_fb(9,"374151"), fill=lgray_fill, align=_left)
        _s(ws1[f"O{row}"], ":",   font=_fn(), fill=lgray_fill, align=_center)
        _s(ws1[f"P{row}"], val_r, font=_fb(9), fill=white_fill, align=_left)

    _field_row(3, "PAM No.",          pam["pam_no"],
                  "Cost Center",      pam.get("cost_center", ""))
    _field_row(4, "Date",             _fmt_date(pam.get("pam_date", "")),
                  "GL Account",       str(pam.get("gl_account", "")))
    _field_row(5, "Requestor's Name", pam.get("requestors_name", ""),
                  "SO / SC",          "")
    _field_row(6, "Department",       "-",
                  "Company",          pam.get("pt", ""))

    def _section(row, title):
        ws1.merge_cells(f"B{row}:Q{row}")
        _s(ws1[f"B{row}"], title, font=_fb(9,"374151"), fill=gray_fill, align=_left)

    def _full_row(row, text, fill=None):
        ws1.merge_cells(f"B{row}:Q{row}")
        _s(ws1[f"B{row}"], text, font=_fn(9), fill=fill or amber_fill, align=_left)

    _section(7, "Business Unit")
    _full_row(8, "☐  Upstream          ☐  Downstream          ☑  Corporate")

    _section(9, "Type of Request")
    _full_row(10, "☐  Downpayment to vendor")
    _full_row(11, "☑  Invoice Payment – Non PO Invoice")
    _full_row(12, "☐  Employee Advance / Reimbursement (Fund Transfer)")

    _section(13, "Invoice Information")

    def _inv_row(row, lbl_l, val_l, lbl_r="", val_r=""):
        ws1.merge_cells(f"C{row}:E{row}")
        ws1.merge_cells(f"G{row}:J{row}")
        _s(ws1[f"C{row}"], lbl_l, font=_fb(9,"374151"), fill=lgray_fill, align=_left)
        _s(ws1[f"F{row}"], ":",   font=_fn(), fill=lgray_fill, align=_center)
        _s(ws1[f"G{row}"], val_l, font=_fb(9), fill=white_fill, align=_left)
        if lbl_r:
            ws1.merge_cells(f"K{row}:M{row}")
            ws1.merge_cells(f"O{row}:Q{row}")
            _s(ws1[f"K{row}"], lbl_r, font=_fb(9,"374151"), fill=lgray_fill, align=_left)
            _s(ws1[f"N{row}"], ":",   font=_fn(), fill=lgray_fill, align=_center)
            _s(ws1[f"O{row}"], val_r, font=_fb(9), fill=white_fill, align=_left)

    _inv_row(14, "Vendor Name",    "Terlampir",
                 "Invoice/Memo No", "-")
    _inv_row(15, "Invoice Amount", _fmt_rp(pam.get("total_amount", 0)),
                 "Expected Due Date", _fmt_date(pam.get("due_date", "")))

    _section(16, "Vendor Bank Account Details")

    def _bank_row(row, label):
        ws1.merge_cells(f"C{row}:E{row}")
        ws1.merge_cells(f"G{row}:Q{row}")
        _s(ws1[f"C{row}"], label,       font=_fb(9,"374151"), fill=lgray_fill, align=_left)
        _s(ws1[f"F{row}"], ":",         font=_fn(), fill=lgray_fill, align=_center)
        _s(ws1[f"G{row}"], "Terlampir", font=_fb(9,"92400E"), fill=amber_fill, align=_left)

    _bank_row(17, "Bank Account Name")
    _bank_row(18, "Bank Name")
    _bank_row(19, "Bank Account Number")

    # Signature block
    ws1.merge_cells("B20:Q20")
    ws1["B20"].fill = gray_fill

    ws1.merge_cells("B21:F24")
    _s(ws1["B21"], "Request by", font=_fb(9,"374151"), fill=lgray_fill, align=_left)
    ws1.merge_cells("H21:Q24")
    _s(ws1["H21"], "Approved by", font=_fb(9,"374151"), fill=lgray_fill, align=_left)

    ws1.merge_cells("B25:F25")
    _s(ws1["B25"], pam.get("requestors_name", ""),
       font=_fb(10,"1E3A5F"), fill=lgray_fill, align=_left)
    ws1.merge_cells("H25:Q25")
    _s(ws1["H25"], f"{approved_by_1}          {approved_by_2}",
       font=_fb(10,"1E3A5F"), fill=lgray_fill, align=_left)

    ws1.merge_cells("B26:Q30")
    _s(ws1["B26"], "Checked by (QA)", font=_fb(9,"374151"), fill=lgray_fill, align=_left)

    for col, w in zip("ABCDEFGHIJKLMNOPQ",
                      [1,8,5,5,5,2,10,5,5,5,5,5,5,5,2,10,10]):
        ws1.column_dimensions[col].width = w

    # ── Sheet 2: Lampiran ────────────────────────────────────────────────────
    ws2 = wb.create_sheet("Lampiran")

    ws2.merge_cells("A1:H1")
    _s(ws2["A1"], "Lampiran — Jadwal Pembayaran Beasiswa",
       font=_fw(11), fill=blue_fill, align=_left)
    ws2.row_dimensions[1].height = 18

    ws2.merge_cells("A2:H2")
    _s(ws2["A2"],
       f"{pam_no}  ·  {pam.get('pt','')}  ·  {_fmt_date(pam.get('pam_date',''))}",
       font=Font(size=8, color="CBD5E1", name="Arial"), fill=blue_fill, align=_left)

    hdr = ["No","Nama Siswa","Bank","No. Rekening","Atas Nama","Kategori","Kode","Amount (Rp)"]
    for c, h in enumerate(hdr, 1):
        cell = ws2.cell(3, c, h)
        cell.font      = _fw(9)
        cell.fill      = blue_fill
        cell.alignment = _center
        cell.border    = _border

    total = 0.0
    for i, pb in enumerate(payments, 1):
        r   = 3 + i
        cat = f"{pb.get('cat1','')}/{pb.get('cat2','')}"
        row_data = [i,
                    pb.get("nama") or pb.get("siswa_code",""),
                    pb.get("bank") or "",
                    pb.get("norek") or "",
                    pb.get("namarek") or "",
                    cat,
                    pb.get("siswa_code",""),
                    float(pb.get("amount",0))]
        f = white_fill if i % 2 else lgray_fill
        for c, v in enumerate(row_data, 1):
            cell            = ws2.cell(r, c, v)
            cell.font       = _fn(9)
            cell.fill       = f
            cell.alignment  = _center if c in (1,3) else _left
            cell.border     = _border
            if c == 8:
                cell.alignment   = Alignment(horizontal="right", vertical="center")
                cell.number_format = '#,##0'
        total += float(pb.get("amount", 0))

    tr = 3 + len(payments) + 1
    ws2.cell(tr, 7, "TOTAL").font      = _fb(9)
    ws2.cell(tr, 7).fill              = PatternFill("solid", fgColor="E8F0FE")
    ws2.cell(tr, 7).alignment         = Alignment(horizontal="right", vertical="center")
    ws2.cell(tr, 7).border            = _border
    tc                 = ws2.cell(tr, 8, total)
    tc.font            = _fb(9)
    tc.fill            = PatternFill("solid", fgColor="E8F0FE")
    tc.alignment       = Alignment(horizontal="right", vertical="center")
    tc.number_format   = '#,##0'
    tc.border          = _border

    for col, w in zip("ABCDEFGH", [5,22,12,16,18,18,10,14]):
        ws2.column_dimensions[col].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
