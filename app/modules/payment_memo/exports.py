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


def _build_pam_table_custom(data: dict) -> Table:
    pam_date    = _fmt_date(data.get("pam_date", ""))
    due_date    = _fmt_date(data.get("due_date", ""))
    invoice_amt = _fmt_rp(data.get("total_amount", 0))

    def _cb(val):
        return "☑" if val else "☐"

    def _maybe_terlampir(val):
        s = str(val) if val is not None else ""
        if not s or s.strip().lower() == "terlampir":
            return _terlampir()
        return _p(s, _S_VAL)

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


def export_pam_pdf_custom(data: dict, payments: list) -> bytes:
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
    for col, w in [("A",3.0),("B",11.15),("C",1.84),("D",7.53),("E",6.43),
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
    _CN        = Alignment(horizontal="center", vertical="center", wrap_text=False)
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

    # Row 11 — BU checkboxes (unmerged single cells)
    ws["E11"].border = _box                         # empty checkbox (Upstream)
    _set("G11", "  Upstream",              align=_L)
    ws["I11"].border = Border(right=_thin)
    ws["J11"].border = Border(top=_thin, bottom=_thin, right=_thin)
    _set("K11", "  Downstream",            align=_L)
    _set("N11", "V",                        align=_C, border=_box)
    _set("O11", "  Corporate",             align=_L)

    # Row 13 — Type of Request header
    _set("B13", "Type of Request ",        align=_L)

    # Row 14 — Downpayment (unchecked)
    ws["E14"].border = _box                         # empty checkbox
    _set("G14", "  Downpayment to vendor", align=_L)

    # Row 15 — Invoice Payment (checked)
    _set("E15", "V",                        align=_C, border=_box)
    _set("G15", "  Invoice Payment – Non PO Invoice", align=_L)

    # Row 16 — Employee Advance (unchecked)
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

    # Rows 29-34 — Request by signature (unmerged, cell-by-cell borders)
    _draw_box(29, 2, 29, 6)
    _set("C29", "Request by",              font=_bold(), align=_CN)
    _draw_box(30, 2, 33, 6)
    _draw_box(34, 2, 34, 6)
    _set("C34", pam.get("requestors_name", ""), align=_CN)

    # Rows 36-42 — Approved by signature (unmerged, cell-by-cell borders)
    _draw_box(36, 2, 36, 11)
    _set("E36", "Approved by",             font=_bold(), align=_CN)
    for _r in range(36, 43):
        ws.cell(_r, 12).border = Border(left=_thin)   # L36:L42 — left edge only
    _draw_box(37, 2, 41, 6)
    _draw_box(37, 7, 41, 11)
    _draw_box(42, 2, 42, 6)
    _draw_box(42, 7, 42, 11)
    _set("C42", approved_by_1,             align=_CN)
    _set("H42", approved_by_2,             align=_CN)

    # Row 43 — Checked by (QA)
    _set("B43", "Checked by (QA)",         font=_bold())

    # Rows 44-48 — QA signature space (unmerged)
    _draw_box(44, 2, 48, 6)

    # ── Sheet 2: Rangkuman PAM (Book8 standard format) ───────────────────────
    ws2 = wb.create_sheet("Rangkuman PAM")

    # Column widths matching Book8
    for _c2, _w2 in [("A",2.77),("B",10.30),("C",1.15),("D",37.84),
                     ("E",37.0), ("F",23.15),("G",1.0), ("H",18.46),("I",2.84)]:
        ws2.column_dimensions[_c2].width = _w2

    # Styles
    _hf2 = PatternFill("solid", fgColor="D9D9D9")  # header fill (theme 0 tint -0.15)
    _t2  = Side(style="thin")
    _k2  = Side(style="thick")

    def _b2(l=False, r=False, t=False, b=False):
        return Border(left=_t2 if l else None, right=_t2 if r else None,
                      top=_t2 if t else None,  bottom=_t2 if b else None)

    def _s2(row, col, val=None, bold=False, sz=11,
            ha=None, va=None, fill=None, bdr=None, fmt=None):
        c2 = ws2.cell(row, col)
        if val is not None:
            c2.value = val
        c2.font = Font(bold=bold, size=sz)
        if ha or va:
            c2.alignment = Alignment(horizontal=ha or "general",
                                     vertical=va or "bottom")
        if fill:
            c2.fill = fill
        if bdr:
            c2.border = bdr
        if fmt:
            c2.number_format = fmt
        return c2

    # Row heights for info rows
    for _ri2 in (2, 3, 4, 5):
        ws2.row_dimensions[_ri2].height = 15.9

    # Rows 2-3: PAM info header
    _s2(2, 2, "NO. ",         bold=True, sz=12, va="top")
    _s2(2, 3, ":",             bold=True, sz=12)
    _s2(2, 4, pam_no,          sz=12,    va="top")
    _s2(2, 6, "COST CENTER ", bold=True, sz=12)
    _s2(2, 7, ":",             bold=True, sz=12)
    _s2(2, 8, pam.get("cost_center", ""), bold=True, sz=12)

    _s2(3, 2, "TANGGAL",      bold=True, sz=12)
    _s2(3, 3, ":",             bold=True, sz=12)
    try:
        _d3v = _dt.strptime(pam.get("pam_date", "")[:10], "%Y-%m-%d")
        _s2(3, 4, _d3v, bold=True, sz=12, ha="left",
            fmt='[$-421]dd\\ mmmm\\ yyyy;@')
    except Exception:
        _s2(3, 4, pam.get("pam_date", ""), bold=True, sz=12, ha="left")
    _s2(3, 6, "GL ACCOUNT     ", bold=True, sz=12)
    _s2(3, 7, ":",               bold=True, sz=12)
    _s2(3, 8, pam.get("gl_account", ""), bold=True, sz=12, ha="left")

    # Split payments: universities (Section 2) vs individuals (Section 1)
    _UNI_KW = ("universitas", "institut ", "akademi", "politeknik",
               "sekolah tinggi", "stie", "stmik", "kelolaan")
    _sec1, _sec2 = [], []
    for _pb2 in payments:
        _check = ((_pb2.get("namarek") or "") + " " +
                  (_pb2.get("nama") or "")).lower()
        if any(_kw2 in _check for _kw2 in _UNI_KW):
            _sec2.append(_pb2)
        else:
            _sec1.append(_pb2)

    def _write_hdr2(r0, sz=11):
        """Write 2-row table header at rows r0 and r0+1."""
        ws2.merge_cells(f"B{r0}:B{r0+1}")
        ch = ws2.cell(r0, 2, "NO")
        ch.font = Font(bold=True, size=sz)
        ch.fill = _hf2
        ch.alignment = Alignment(horizontal="center", vertical="center")
        ch.border = Border(left=_t2, right=_t2, top=_t2, bottom=_t2)
        ws2.cell(r0+1, 2).border = Border(left=_t2, right=_t2, bottom=_t2)
        # C spacer
        ws2.cell(r0,   3).fill = _hf2
        ws2.cell(r0,   3).border = _b2(l=True, t=True)
        ws2.cell(r0+1, 3).fill = _hf2
        ws2.cell(r0+1, 3).border = _b2(l=True, b=True)
        # D: "NAMA " / "REKENING"
        for _rh, _th in [(r0, "NAMA "), (r0+1, "REKENING")]:
            ch = ws2.cell(_rh, 4, _th)
            ch.font = Font(bold=True, size=sz)
            ch.fill = _hf2
            ch.alignment = Alignment(horizontal="center", vertical="center")
            ch.border = Border(right=_t2,
                               top=(_t2 if _rh == r0   else None),
                               bottom=(_t2 if _rh == r0+1 else None))
        # E: BANK
        for _rh, _th in [(r0, "BANK"), (r0+1, None)]:
            ch = ws2.cell(_rh, 5, _th)
            ch.font = Font(bold=True, size=sz)
            ch.fill = _hf2
            ch.alignment = Alignment(horizontal="center")
            ch.border = Border(left=_t2, right=_t2,
                               top=(_t2 if _rh == r0   else None),
                               bottom=(_t2 if _rh == r0+1 else None))
        # F: "NO" / "REKENING"
        for _rh, _th in [(r0, "NO"), (r0+1, "REKENING")]:
            ch = ws2.cell(_rh, 6, _th)
            ch.font = Font(bold=True, size=sz)
            ch.fill = _hf2
            ch.alignment = Alignment(horizontal="center")
            ch.border = Border(left=_t2,
                               top=(_t2 if _rh == r0   else None),
                               bottom=(_t2 if _rh == r0+1 else None))
        # G spacer
        ws2.cell(r0,   7).fill = _hf2
        ws2.cell(r0,   7).border = _b2(r=True, t=True)
        ws2.cell(r0+1, 7).fill = _hf2
        ws2.cell(r0+1, 7).border = _b2(r=True, b=True)
        # H: "TOTAL" / "PEMBAYARAN"
        for _rh, _th in [(r0, "TOTAL"), (r0+1, "PEMBAYARAN")]:
            ch = ws2.cell(_rh, 8, _th)
            ch.font = Font(bold=True, size=sz)
            ch.fill = _hf2
            ch.alignment = Alignment(horizontal="center")
            ch.border = Border(left=_t2, right=_t2,
                               top=(_t2 if _rh == r0   else None),
                               bottom=(_t2 if _rh == r0+1 else None))

    def _write_data2(row, seq, namarek, bank, norek, amt, sz=12):
        ws2.row_dimensions[row].height = 29.25
        fn2 = Font(size=sz)
        ws2.cell(row, 2, str(seq)).font = fn2
        ws2.cell(row, 2).alignment = Alignment(horizontal="center", vertical="center")
        ws2.cell(row, 2).border = Border(left=_t2, right=_t2, top=_t2, bottom=_t2)
        ws2.cell(row, 3).border = _b2(l=True, t=True, b=True)
        ws2.cell(row, 4, namarek).font = fn2
        ws2.cell(row, 4).alignment = Alignment(horizontal="left", vertical="center")
        ws2.cell(row, 4).border = Border(right=_t2, top=_t2, bottom=_t2)
        ws2.cell(row, 5, bank).font = fn2
        ws2.cell(row, 5).alignment = Alignment(horizontal="left", vertical="center")
        ws2.cell(row, 5).border = Border(left=_t2, right=_t2, top=_t2, bottom=_t2)
        ws2.cell(row, 6, norek).font = fn2
        ws2.cell(row, 6).alignment = Alignment(horizontal="center", vertical="center")
        ws2.cell(row, 6).border = _b2(l=True, t=True, b=True)
        ws2.cell(row, 7).border = _b2(r=True, t=True, b=True)
        ws2.cell(row, 8, amt).font = fn2
        ws2.cell(row, 8).alignment = Alignment(horizontal="center", vertical="center")
        ws2.cell(row, 8).border = Border(left=_t2, right=_t2, top=_t2, bottom=_t2)
        ws2.cell(row, 8).number_format = '#,##0'

    def _write_tot2(row, total_val, label="Total", sz=12, thick_top=False):
        ws2.merge_cells(f"B{row}:F{row}")
        fn2 = Font(bold=True, size=sz)
        ws2.cell(row, 2, label).font = fn2
        ws2.cell(row, 2).alignment = Alignment(horizontal="center", vertical="center")
        ws2.cell(row, 2).border = Border(left=_t2, top=_t2, bottom=_t2)
        for _col2 in range(3, 7):  # C–F: top+bottom, no sides (within merge)
            ws2.cell(row, _col2).border = Border(top=_t2, bottom=_t2)
        ws2.cell(row, 7).border = Border(
            right=_t2, bottom=_t2,
            top=(_k2 if thick_top else None))
        ws2.cell(row, 8, total_val).font = fn2
        ws2.cell(row, 8).alignment = Alignment(horizontal="center", vertical="center")
        ws2.cell(row, 8).border = Border(
            left=_t2, right=_t2, bottom=_t2,
            top=(_k2 if thick_top else _t2))
        ws2.cell(row, 8).number_format = '#,##0'

    # ── Section 1: individual / student payments ──────────────────────────────
    _cur2 = 6
    _write_hdr2(_cur2, sz=11)
    _cur2 += 2
    _tot1 = 0.0
    for _i2, _pb2 in enumerate(_sec1, 1):
        _nm2  = _pb2.get("namarek") or _pb2.get("nama") or _pb2.get("siswa_code", "")
        _bk2  = _pb2.get("bank") or ""
        _nr2  = _pb2.get("norek") or ""
        _am2  = float(_pb2.get("amount", 0))
        _write_data2(_cur2, _i2, _nm2, _bk2, _nr2, _am2, sz=12)
        _tot1 += _am2
        _cur2 += 1
    _write_tot2(_cur2, _tot1, "Total", sz=12, thick_top=True)
    _cur2 += 1

    _grand2 = _tot1

    # ── Section 2: university payments (if any) ───────────────────────────────
    if _sec2:
        _cur2 += 1  # spacer row
        ws2.cell(_cur2, 2, "Dibayarkan ke Universitas").font = Font(bold=True, size=11)
        _cur2 += 1
        _write_hdr2(_cur2, sz=10)
        _cur2 += 2
        _tot2 = 0.0
        for _i2, _pb2 in enumerate(_sec2, 1):
            _nm2 = _pb2.get("namarek") or _pb2.get("nama") or _pb2.get("siswa_code", "")
            _bk2 = _pb2.get("bank") or ""
            _nr2 = _pb2.get("norek") or ""
            _am2 = float(_pb2.get("amount", 0))
            _write_data2(_cur2, _i2, _nm2, _bk2, _nr2, _am2, sz=10)
            _tot2 += _am2
            _cur2 += 1
        _write_tot2(_cur2, _tot2, "Total", sz=10, thick_top=False)
        _cur2 += 1
        _grand2 += _tot2

        # Spacer + Grand Total
        _cur2 += 1
        ws2.merge_cells(f"B{_cur2}:F{_cur2}")
        _fg = Font(bold=True, size=10)
        ws2.cell(_cur2, 2, "Grand Total").font = _fg
        ws2.cell(_cur2, 2).alignment = Alignment(horizontal="center", vertical="center")
        ws2.cell(_cur2, 2).border = Border(left=_t2, top=_t2, bottom=_t2)
        for _col2 in range(3, 7):
            ws2.cell(_cur2, _col2).border = Border(top=_t2, bottom=_t2)
        ws2.cell(_cur2, 7).border = _b2(r=True, t=True, b=True)
        ws2.cell(_cur2, 8, _grand2).font = _fg
        ws2.cell(_cur2, 8).alignment = Alignment(horizontal="center", vertical="center")
        ws2.cell(_cur2, 8).border = Border(left=_t2, right=_t2, top=_t2, bottom=_t2)
        ws2.cell(_cur2, 8).number_format = '#,##0'

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


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
