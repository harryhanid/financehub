import io
import math
from datetime import datetime
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

def _fmt(v):
    if not v: return '-'
    is_neg = False
    if v < 0:
        is_neg = True
        v = abs(v)
        
    if v >= 1e9:
        s = '%.2f' % (v/1e9)
        s = s.rstrip('0').rstrip('.')
        res = s.replace('.', ',') + ' Milyar'
    elif v >= 1e6:
        s = '%.1f' % (v/1e6)
        s = s.rstrip('0').rstrip('.')
        res = s.replace('.', ',') + ' Juta'
    elif v >= 1e3:
        s = '%.1f' % (v/1e3)
        s = s.rstrip('0').rstrip('.')
        res = s.replace('.', ',') + ' Ribu'
    else:
        res = f"{v:,.0f}".replace(',', '.')
        
    if is_neg:
        return f"({res})"
    return res

def _draw_rect(slide, left, top, width, height, rgb, line_rgb=None, rounded=False):
    stype = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(stype, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(*rgb)
    if line_rgb:
        shape.line.color.rgb = RGBColor(*line_rgb)
        shape.line.width = Pt(1.5)
    else:
        shape.line.fill.background()
    return shape

def _add_text(slide, text, left, top, width, height, size=12, bold=False, rgb=(0,0,0), align=PP_ALIGN.LEFT):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = align
    p.font.name = 'Segoe UI'
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = RGBColor(*rgb)
    return txBox

def _draw_table(slide, left, top, width, rows, total_data, header_rgb, mode_key):
    table_shape = slide.shapes.add_table(7, 5, left, top, width, Inches(2.6))
    table = table_shape.table
    
    headers = ["Penerima", "Plafon", "Klaim", "Dibayar", "Saldo"]
    
    table.columns[0].width = int(width * 0.28)
    table.columns[1].width = int(width * 0.18)
    table.columns[2].width = int(width * 0.18)
    table.columns[3].width = int(width * 0.18)
    table.columns[4].width = int(width * 0.18)
    
    def _cell(r, c, text, bg_rgb, text_rgb, bold=False, align=PP_ALIGN.CENTER):
        cell = table.cell(r, c)
        cell.text = text
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(*bg_rgb)
        
        p = cell.text_frame.paragraphs[0]
        p.alignment = align
        p.font.name = 'Segoe UI'
        p.font.size = Pt(10)
        p.font.bold = bold
        p.font.color.rgb = RGBColor(*text_rgb)
            
    for c, text in enumerate(headers):
        _cell(0, c, text, header_rgb, (255,255,255), bold=True)
        
    for r in range(5):
        bg = (255,255,255) if r % 2 == 0 else (248,249,250)
        if r < len(rows):
            row_data = rows[r]
            nama = row_data["nama"]
            if len(nama) > 18:
                parts = nama.split()
                if len(parts) > 1:
                    nama = parts[0] + " " + " ".join([p[0] + "." for p in parts[1:]])
            
            c_data = row_data[mode_key]
            plafon = c_data["plafon"]
            klaim = c_data["klaim"]
            dibayar = c_data["dibayar"]
            saldo = c_data.get("saldo", 0)
            
            _cell(r+1, 0, nama, bg, (0,0,0), align=PP_ALIGN.LEFT)
            _cell(r+1, 1, _fmt(plafon), bg, (0,0,0))
            _cell(r+1, 2, _fmt(klaim), bg, (0,0,0))
            _cell(r+1, 3, _fmt(dibayar), bg, (0,0,0))
            _cell(r+1, 4, _fmt(saldo), bg, (0,0,0))
        else:
            for c in range(5):
                _cell(r+1, c, "", bg, (0,0,0))
                
    footer_bg = header_rgb
    _cell(6, 0, "Subtotal", footer_bg, (255,255,255), bold=True, align=PP_ALIGN.LEFT)
    if total_data:
        plafon = total_data.get("plafon", 0)
        klaim = total_data.get("klaim", 0)
        dibayar = total_data.get("dibayar", 0)
        saldo = total_data.get("saldo", 0)
        _cell(6, 1, _fmt(plafon), footer_bg, (255,255,255), bold=True)
        _cell(6, 2, _fmt(klaim), footer_bg, (255,255,255), bold=True)
        _cell(6, 3, _fmt(dibayar), footer_bg, (255,255,255), bold=True)
        _cell(6, 4, _fmt(saldo), footer_bg, (255,255,255), bold=True)
    else:
        for c in range(1, 5):
            _cell(6, c, "-", footer_bg, (255,255,255), bold=True)

def build_report_pptx(data: dict, mode: str = "ytd") -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    sections = {s["key"]: s for s in data["sections"]}
    pengobatan = sections.get("KESEHATAN", {})
    pendidikan = sections.get("PENDIDIKAN", {})
    
    peng_rows = pengobatan.get("recap", [])
    pend_rows = pendidikan.get("recap", [])
    
    mode_key = "cur" if mode == "fy" else "cum"
    
    peng_rows = [r for r in peng_rows if r[mode_key]["plafon"] != 0 or r[mode_key]["klaim"] != 0 or r[mode_key]["dibayar"] != 0]
    pend_rows = [r for r in pend_rows if r[mode_key]["plafon"] != 0 or r[mode_key]["klaim"] != 0 or r[mode_key]["dibayar"] != 0]
    
    peng_rows.sort(key=lambda x: x[mode_key]["plafon"], reverse=True)
    pend_rows.sort(key=lambda x: x[mode_key]["plafon"], reverse=True)
    
    chunk_size = 5
    max_len = max(len(peng_rows), len(pend_rows))
    pages = math.ceil(max_len / chunk_size) if max_len > 0 else 1
    
    g_tot = data["combined_total"][mode_key]
    peng_penerima = len(peng_rows)
    pend_penerima = len(pend_rows)
    tot_penerima = peng_penerima + pend_penerima
    
    months = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    eng_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    import calendar
    now = datetime.now()
    report_month = data.get("report_month", now.month)
    report_year = data.get("report_year", now.year)
    
    if report_year == now.year and report_month == now.month:
        day = now.day
    else:
        day = calendar.monthrange(report_year, report_month)[1]
        
    date_str = f"{day} {months[report_month-1]} {report_year}"
    eng_date_str = f"{day} {eng_months[report_month-1]} {report_year}"
    print_date = f"{now.day} {eng_months[now.month-1]} {now.year}"
    
    green = (0, 176, 80)
    purple = (112, 48, 160)
    
    for page in range(pages):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        
        # 1. Header 
        _add_text(slide, "SUMMARY OVERVIEW", Inches(0.5), Inches(0.2), width=Inches(6), height=Inches(0.5), size=28, bold=True)
        _add_text(slide, "Sahabat ETF", Inches(0.5), Inches(0.65), width=Inches(6), height=Inches(0.4), size=20, bold=True)
        _draw_rect(slide, Inches(0.5), Inches(1.10), Inches(6), Inches(0.02), (0,0,0))
        
        # Top-right Report Mode Badge
        if mode == "fy":
            report_title = "Year to Date Report"
            report_period = f"from 1 Jan to {eng_date_str}"
            badge_bg = (235, 250, 240)
            badge_line = (180, 230, 200)
            badge_text = (30, 120, 70)
        else:
            report_title = "Cumulative Report"
            report_period = f"from Beg. to {eng_date_str}"
            badge_bg = (255, 250, 230)
            badge_line = (240, 220, 170)
            badge_text = (120, 80, 30)

        # Compact badge (Left: 10.0, Width: 2.8, Height: 0.55)
        _draw_rect(slide, Inches(10.0), Inches(0.3), Inches(2.8), Inches(0.55), badge_bg, rounded=True, line_rgb=badge_line)
        
        # Calendar Icon
        _add_text(slide, "📅", Inches(10.1), Inches(0.37), width=Inches(0.4), height=Inches(0.4), size=22, align=PP_ALIGN.LEFT)
        
        # Right-aligned text
        _add_text(slide, report_title, Inches(10.6), Inches(0.35), width=Inches(2.0), height=Inches(0.2), size=12, bold=True, align=PP_ALIGN.RIGHT, rgb=badge_text)
        _add_text(slide, report_period, Inches(10.6), Inches(0.55), width=Inches(2.0), height=Inches(0.2), size=10, bold=False, align=PP_ALIGN.RIGHT, rgb=badge_text)
        
        # 2. Top Left Box
        _draw_rect(slide, Inches(0.5), Inches(1.3), Inches(7.5), Inches(1.2), (235, 245, 255), rounded=True, line_rgb=(180, 210, 240))
        
        # Big icon 1
        _add_text(slide, "👥", Inches(0.7), Inches(1.4), width=Inches(0.8), height=Inches(0.8), size=40)
        _add_text(slide, "Total Penerima Bantuan", Inches(1.6), Inches(1.4), width=Inches(2.5), height=Inches(0.3), size=14)
        
        # Fix width to avoid wrapping '11'
        _add_text(slide, f"{tot_penerima}", Inches(1.6), Inches(1.7), width=Inches(1.0), height=Inches(0.5), size=26, bold=True)
        _add_text(slide, "orang", Inches(2.3), Inches(1.9), width=Inches(1.0), height=Inches(0.3), size=14)
        
        # Divider line
        _draw_rect(slide, Inches(4.3), Inches(1.4), Inches(0.02), Inches(1.0), (150,150,150))
        
        # Big icon 2
        _add_text(slide, "🌱", Inches(4.5), Inches(1.4), width=Inches(0.8), height=Inches(0.8), size=40)
        _add_text(slide, "Bantuan Terealisasi", Inches(5.4), Inches(1.4), width=Inches(2.5), height=Inches(0.3), size=14)
        _add_text(slide, f"{_fmt(g_tot['dibayar'])}", Inches(5.4), Inches(1.7), width=Inches(2.5), height=Inches(0.5), size=26, bold=True)
        
        # 3. Top Right Box
        _draw_rect(slide, Inches(8.2), Inches(1.3), Inches(4.6), Inches(1.2), (235, 245, 255), rounded=True, line_rgb=(180, 210, 240))
        _add_text(slide, "Komposisi Penerima Bantuan", Inches(9.2), Inches(1.4), width=Inches(3.5), height=Inches(0.3), size=16, align=PP_ALIGN.CENTER)
        
        # Draw a custom pie chart shape using OVAL and ARC/PIE
        bg_pie = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(8.4), Inches(1.5), Inches(0.6), Inches(0.6))
        bg_pie.fill.solid(); bg_pie.fill.fore_color.rgb = RGBColor(*green); bg_pie.line.fill.background()
        pie_slice = slide.shapes.add_shape(MSO_SHAPE.PIE, Inches(8.4), Inches(1.5), Inches(0.6), Inches(0.6))
        pie_slice.fill.solid(); pie_slice.fill.fore_color.rgb = RGBColor(*purple); pie_slice.line.fill.background()
        
        _add_text(slide, "Pengobatan", Inches(9.4), Inches(1.8), width=Inches(1.5), height=Inches(0.3), size=14, bold=True, align=PP_ALIGN.CENTER, rgb=green)
        _add_text(slide, f"{peng_penerima} orang", Inches(9.4), Inches(2.0), width=Inches(1.5), height=Inches(0.3), size=14, align=PP_ALIGN.CENTER)
        
        _add_text(slide, "Pendidikan", Inches(11.0), Inches(1.8), width=Inches(1.5), height=Inches(0.3), size=14, bold=True, align=PP_ALIGN.CENTER, rgb=purple)
        _add_text(slide, f"{pend_penerima} orang", Inches(11.0), Inches(2.0), width=Inches(1.5), height=Inches(0.3), size=14, align=PP_ALIGN.CENTER)
        
        # 4. Tables Box
        table_top = Inches(2.7)
        _draw_rect(slide, Inches(0.5), table_top, Inches(6.0), Inches(3.6), (255,255,255), line_rgb=(100,100,100))
        _add_text(slide, "✚", Inches(0.55), Inches(2.73), width=Inches(0.5), height=Inches(0.5), size=30, bold=True, rgb=(230, 60, 60))
        _add_text(slide, "Bantuan Pengobatan", Inches(1.0), Inches(2.8), width=Inches(3), height=Inches(0.4), size=16, bold=True, rgb=green)
        _draw_rect(slide, Inches(5.0), Inches(2.85), Inches(1.3), Inches(0.3), green, rounded=True)
        _add_text(slide, f"{peng_penerima} Penerima", Inches(5.0), Inches(2.87), width=Inches(1.3), height=Inches(0.3), size=11, bold=True, align=PP_ALIGN.CENTER, rgb=(255,255,255))
        
        _draw_rect(slide, Inches(6.8), table_top, Inches(6.0), Inches(3.6), (255,255,255), line_rgb=(100,100,100))
        _add_text(slide, "🎓", Inches(6.85), Inches(2.73), width=Inches(0.5), height=Inches(0.5), size=26, bold=True)
        _add_text(slide, "Bantuan Pendidikan", Inches(7.4), Inches(2.8), width=Inches(3), height=Inches(0.4), size=16, bold=True, rgb=purple)
        _draw_rect(slide, Inches(11.3), Inches(2.85), Inches(1.3), Inches(0.3), purple, rounded=True)
        _add_text(slide, f"{pend_penerima} Penerima", Inches(11.3), Inches(2.87), width=Inches(1.3), height=Inches(0.3), size=11, bold=True, align=PP_ALIGN.CENTER, rgb=(255,255,255))
        
        p_start = page * chunk_size
        p_end = p_start + chunk_size
        
        _draw_table(slide, Inches(0.6), Inches(3.3), Inches(5.8), peng_rows[p_start:p_end], pengobatan.get("total", {}).get(mode_key, {}), green, mode_key)
        _draw_table(slide, Inches(6.9), Inches(3.3), Inches(5.8), pend_rows[p_start:p_end], pendidikan.get("total", {}).get(mode_key, {}), purple, mode_key)
        
        # 5. Bottom Total Box
        _draw_rect(slide, Inches(0.5), Inches(6.4), Inches(12.3), Inches(0.9), (255,255,255), line_rgb=(100,100,100))
        
        # Big Icon Calculator
        _add_text(slide, "🧮", Inches(0.6), Inches(6.5), width=Inches(0.6), height=Inches(0.6), size=36)
        _add_text(slide, "Total Pengobatan\n& Pendidikan", Inches(1.3), Inches(6.5), width=Inches(1.8), height=Inches(0.6), size=12, bold=True)
        
        # Divider
        _draw_rect(slide, Inches(3.1), Inches(6.5), Inches(0.01), Inches(0.7), (200,200,200))
        
        box_w = Inches(2.3)
        _add_text(slide, "💼", Inches(3.2), Inches(6.5), width=Inches(0.6), height=Inches(0.6), size=32)
        _add_text(slide, "Total Plafon", Inches(3.8), Inches(6.5), width=box_w, height=Inches(0.3), size=12)
        _add_text(slide, f"Rp {_fmt(g_tot['plafon'])}", Inches(3.8), Inches(6.8), width=box_w, height=Inches(0.4), size=14, bold=True)

        _add_text(slide, "⏩", Inches(5.5), Inches(6.5), width=Inches(0.6), height=Inches(0.6), size=32)
        _add_text(slide, "Total Klaim", Inches(6.1), Inches(6.5), width=box_w, height=Inches(0.3), size=12)
        _add_text(slide, f"Rp {_fmt(g_tot['klaim'])}", Inches(6.1), Inches(6.8), width=box_w, height=Inches(0.4), size=14, bold=True)

        _add_text(slide, "✅", Inches(7.8), Inches(6.5), width=Inches(0.6), height=Inches(0.6), size=32)
        _add_text(slide, "Total Dibayar", Inches(8.4), Inches(6.5), width=box_w, height=Inches(0.3), size=12)
        _add_text(slide, f"Rp {_fmt(g_tot['dibayar'])}", Inches(8.4), Inches(6.8), width=box_w, height=Inches(0.4), size=14, bold=True)
        
        _add_text(slide, "💰", Inches(10.1), Inches(6.5), width=Inches(0.6), height=Inches(0.6), size=32)
        _add_text(slide, "Total Saldo", Inches(10.7), Inches(6.5), width=box_w, height=Inches(0.3), size=12)
        _add_text(slide, f"Rp {_fmt(g_tot.get('saldo', 0))}", Inches(10.7), Inches(6.8), width=box_w, height=Inches(0.4), size=14, bold=True)
        
        # 6. Page Numbering
        _add_text(slide, f"Page {page+1} of {pages}", Inches(11.5), Inches(7.3), width=Inches(1.5), height=Inches(0.2), size=10, bold=False, rgb=(120,120,120), align=PP_ALIGN.RIGHT)
        
    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()
