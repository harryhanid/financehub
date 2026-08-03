path = r"C:\Financehub\app\modules\sponsorship\exports.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
    'ws.append([f"RANGKUMAN SPONSORSHIP {data[\'tahun\']} - in Rp Full Amount"])\n        row = ws.max_row',
    'ws.append([f"RANGKUMAN SPONSORSHIP {data[\'tahun\']} - in Rp Full Amount"])\n        row = ws.max_row\n        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)'
)

# And merge the first title too
c = c.replace(
    'ws.append([f"RANGKUMAN SPONSORSHIP - in Rp Full Amount"])\n    ws["A1"].font = ARIAL_11_BOLD',
    'ws.append([f"RANGKUMAN SPONSORSHIP - in Rp Full Amount"])\n    ws["A1"].font = ARIAL_11_BOLD\n    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done")
