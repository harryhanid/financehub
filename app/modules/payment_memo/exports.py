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
