path = r"C:\Financehub\app\modules\beasiswa\routes.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

import re

# 1. Update Payment Detail (remove Perusahaan)
c = c.replace(
"""        # Payment detail
        elems.append(Paragraph("Detail Payment", styles["Heading2"]))
        pay_data = [["Kategori 1", "Kategori 2", "Tanggal", "PAM", "Perusahaan", "Pillar", "Amount (Rp)", "Status"]]
        pay_total = 0
        for r in data["payment_rows"]:
            a = r.get("amount", 0); pay_total += a
            pay_data.append([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                             r.get("pam",""), r.get("perusahaan",""), r.get("pillar",""),
                             f"{a:,.0f}", r.get("status","")])
        if data["payment_rows"]:
            pay_data.append(["", "TOTAL", "", "", "", "", f"{pay_total:,.0f}", ""])
        pt = Table(pay_data, colWidths=[2.5*cm, 2.5*cm, 2.0*cm, 2.0*cm, 2.5*cm, 2.0*cm, 2.5*cm, 1.8*cm], repeatRows=1)
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#065f46")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
            ("ALIGN", (6,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        elems.append(pt)""",
"""        # Text wrapping style for tables
        cell_style = styles["Normal"].clone('cell_style')
        cell_style.fontSize = 8
        cell_style.leading = 10
        cell_style.wordWrap = 'CJK'
        
        def wrap_row(row, is_header=False, is_footer=False):
            wrapped = []
            for item in row:
                if is_header or is_footer:
                    wrapped.append(item)
                else:
                    wrapped.append(Paragraph(str(item), cell_style) if item else "")
            return wrapped

        # Payment detail
        elems.append(Paragraph("Detail Payment", styles["Heading2"]))
        pay_headers = ["Kategori 1", "Kategori 2", "Tanggal", "PAM", "Pillar", "Amount (Rp)", "Status"]
        pay_data = [wrap_row(pay_headers, is_header=True)]
        pay_total = 0
        for r in data["payment_rows"]:
            a = r.get("amount", 0); pay_total += a
            pay_data.append(wrap_row([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                             r.get("pam",""), r.get("pillar",""),
                             f"{a:,.0f}", r.get("status","")]))
        if data["payment_rows"]:
            pay_data.append(wrap_row(["", "TOTAL", "", "", "", f"{pay_total:,.0f}", ""], is_footer=True))
        
        # Adjust column widths to distribute the removed 2.5cm
        pt = Table(pay_data, colWidths=[2.8*cm, 3.2*cm, 2.0*cm, 3.5*cm, 2.0*cm, 2.5*cm, 1.8*cm], repeatRows=1)
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#065f46")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
            ("ALIGN", (5,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        elems.append(pt)"""
)

# 2. Update Budget Detail to also wrap text (using the same wrap_row logic)
# Wait, wrap_row might not be defined above. I'll define it before Budget detail.
c = c.replace(
"""        # Budget detail
        elems.append(Paragraph("Detail Budget", styles["Heading2"]))
        bgt_data = [["Kategori 1", "Kategori 2", "Tanggal", "Pillar", "Amount (Rp)"]]
        bgt_total = 0
        for r in data["budget_rows"]:
            a = r.get("amount", 0); bgt_total += a
            bgt_data.append([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                             r.get("pillar",""), f"{a:,.0f}"])
        if data["budget_rows"]:
            bgt_data.append(["", "TOTAL", "", "", f"{bgt_total:,.0f}"])
        bt = Table(bgt_data, colWidths=[3.5*cm, 4*cm, 2.5*cm, 3*cm, 4*cm], repeatRows=1)
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a56db")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
            ("ALIGN", (4,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        elems += [bt, Spacer(1, 0.4*cm)]""",
"""        # Text wrapping style for tables
        cell_style = styles["Normal"].clone('cell_style')
        cell_style.fontSize = 8
        cell_style.leading = 10
        cell_style.wordWrap = 'CJK'
        
        def wrap_row(row, is_header=False, is_footer=False):
            wrapped = []
            for item in row:
                if is_header or is_footer:
                    wrapped.append(item)
                else:
                    wrapped.append(Paragraph(str(item), cell_style) if item else "")
            return wrapped

        # Budget detail
        elems.append(Paragraph("Detail Budget", styles["Heading2"]))
        bgt_headers = ["Kategori 1", "Kategori 2", "Tanggal", "Pillar", "Amount (Rp)"]
        bgt_data = [wrap_row(bgt_headers, is_header=True)]
        bgt_total = 0
        for r in data["budget_rows"]:
            a = r.get("amount", 0); bgt_total += a
            bgt_data.append(wrap_row([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                             r.get("pillar",""), f"{a:,.0f}"]))
        if data["budget_rows"]:
            bgt_data.append(wrap_row(["", "TOTAL", "", "", f"{bgt_total:,.0f}"], is_footer=True))
        bt = Table(bgt_data, colWidths=[3.5*cm, 4*cm, 2.5*cm, 3*cm, 4*cm], repeatRows=1)
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a56db")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
            ("ALIGN", (4,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        elems += [bt, Spacer(1, 0.4*cm)]"""
)

# And remove the duplicate `cell_style` definition that will be pasted twice.
# We can just remove the second one.
c = c.replace(
"""        # Text wrapping style for tables
        cell_style = styles["Normal"].clone('cell_style')
        cell_style.fontSize = 8
        cell_style.leading = 10
        cell_style.wordWrap = 'CJK'
        
        def wrap_row(row, is_header=False, is_footer=False):
            wrapped = []
            for item in row:
                if is_header or is_footer:
                    wrapped.append(item)
                else:
                    wrapped.append(Paragraph(str(item), cell_style) if item else "")
            return wrapped

        # Payment detail""",
"""        # Payment detail"""
)


with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done pdf update")
