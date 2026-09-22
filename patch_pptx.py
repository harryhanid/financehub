with open('app/modules/sahabat_etf/report_pptx.py', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Update headers
c = c.replace(
    'headers = ["Penerima", "Budget", "Realisasi", "On Progress", "Sisa Budget"]',
    'headers = ["Penerima", "Plafon", "Klaim", "Dibayar", "Saldo"]'
)

# 2. Update table cells logic
old_cells = """            plafon = c_data["plafon"]
            realisasi = c_data["dibayar"]
            on_prog = c_data["klaim"] - c_data["dibayar"]
            sisa = c_data["plafon"] - c_data["klaim"]
            
            _cell(r+1, 0, nama, bg, (0,0,0), align=PP_ALIGN.LEFT)
            _cell(r+1, 1, _fmt(plafon), bg, (0,0,0))
            _cell(r+1, 2, _fmt(realisasi), bg, (0,0,0))
            _cell(r+1, 3, _fmt(on_prog), bg, (0,0,0))
            _cell(r+1, 4, _fmt(sisa), bg, (0,0,0))"""

new_cells = """            plafon = c_data["plafon"]
            klaim = c_data["klaim"]
            dibayar = c_data["dibayar"]
            saldo = c_data.get("saldo", 0)
            
            _cell(r+1, 0, nama, bg, (0,0,0), align=PP_ALIGN.LEFT)
            _cell(r+1, 1, _fmt(plafon), bg, (0,0,0))
            _cell(r+1, 2, _fmt(klaim), bg, (0,0,0))
            _cell(r+1, 3, _fmt(dibayar), bg, (0,0,0))
            _cell(r+1, 4, _fmt(saldo), bg, (0,0,0))"""
c = c.replace(old_cells, new_cells)

# 3. Update table footer logic
old_footer = """    if total_data:
        plafon = total_data.get("plafon", 0)
        realisasi = total_data.get("dibayar", 0)
        on_prog = total_data.get("klaim", 0) - realisasi
        sisa = plafon - total_data.get("klaim", 0)
        _cell(6, 1, _fmt(plafon), footer_bg, (255,255,255), bold=True)
        _cell(6, 2, _fmt(realisasi), footer_bg, (255,255,255), bold=True)
        _cell(6, 3, _fmt(on_prog), footer_bg, (255,255,255), bold=True)
        _cell(6, 4, _fmt(sisa), footer_bg, (255,255,255), bold=True)"""

new_footer = """    if total_data:
        plafon = total_data.get("plafon", 0)
        klaim = total_data.get("klaim", 0)
        dibayar = total_data.get("dibayar", 0)
        saldo = total_data.get("saldo", 0)
        _cell(6, 1, _fmt(plafon), footer_bg, (255,255,255), bold=True)
        _cell(6, 2, _fmt(klaim), footer_bg, (255,255,255), bold=True)
        _cell(6, 3, _fmt(dibayar), footer_bg, (255,255,255), bold=True)
        _cell(6, 4, _fmt(saldo), footer_bg, (255,255,255), bold=True)"""
c = c.replace(old_footer, new_footer)

# 4. Update the bottom summary box labels and logic
old_bottom = """        # Divider
        _draw_rect(slide, Inches(3.1), Inches(6.5), Inches(0.01), Inches(0.7), (200,200,200))
        
        box_w = Inches(2.3)
        _add_text(slide, "💼", Inches(3.2), Inches(6.5), width=Inches(0.6), height=Inches(0.6), size=32)
        _add_text(slide, "Total Budget", Inches(3.8), Inches(6.5), width=box_w, height=Inches(0.3), size=12)
        _add_text(slide, f"Rp {_fmt(g_tot['plafon'])}", Inches(3.8), Inches(6.8), width=box_w, height=Inches(0.4), size=14, bold=True)

        _add_text(slide, "✅", Inches(5.5), Inches(6.5), width=Inches(0.6), height=Inches(0.6), size=32)
        _add_text(slide, "Realisasi", Inches(6.1), Inches(6.5), width=box_w, height=Inches(0.3), size=12)
        _add_text(slide, f"Rp {_fmt(g_tot['dibayar'])}", Inches(6.1), Inches(6.8), width=box_w, height=Inches(0.4), size=14, bold=True)

        _add_text(slide, "⏩", Inches(7.8), Inches(6.5), width=Inches(0.6), height=Inches(0.6), size=32)
        _add_text(slide, "On progress", Inches(8.4), Inches(6.5), width=box_w, height=Inches(0.3), size=12)
        _add_text(slide, f"Rp {_fmt(g_tot['klaim'] - g_tot['dibayar'])}", Inches(8.4), Inches(6.8), width=box_w, height=Inches(0.4), size=14, bold=True)
        
        _add_text(slide, "💰", Inches(10.1), Inches(6.5), width=Inches(0.6), height=Inches(0.6), size=32)
        _add_text(slide, "Sisa Budget", Inches(10.7), Inches(6.5), width=box_w, height=Inches(0.3), size=12)
        _add_text(slide, f"Rp {_fmt(g_tot['plafon'] - g_tot['klaim'])}", Inches(10.7), Inches(6.8), width=box_w, height=Inches(0.4), size=14, bold=True)"""

new_bottom = """        # Divider
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
        _add_text(slide, f"Rp {_fmt(g_tot.get('saldo', 0))}", Inches(10.7), Inches(6.8), width=box_w, height=Inches(0.4), size=14, bold=True)"""
c = c.replace(old_bottom, new_bottom)

with open('app/modules/sahabat_etf/report_pptx.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("PPTX Logic Patched!")
