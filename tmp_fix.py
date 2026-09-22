import re

with open(r'app\modules\sahabat_etf\report_xlsx.py', 'r', encoding='utf-8') as f:
    content = f.read()

# _set_column_widths
content = re.sub(
    r'\"G\": 13.92, \"O\": 16.69',
    r'\"G\": 13.92, \"Q\": 16.69',
    content
)

# _write_title
content = content.replace('ws.merge_cells(f\"B{row}:N{row}\")', 'ws.merge_cells(f\"B{row}:P{row}\")')
content = content.replace('_set(ws, f\"O{row}\",', '_set(ws, f\"Q{row}\",')

# _write_header
content = re.sub(
    r'fill = _FILL_GREEN if col in \(\"K\", \"L\", \"M\", \"N\"\) else _FILL_NAVY',
    r'fill = _FILL_GREEN if col in (\"L\", \"M\", \"N\", \"O\", \"P\") else _FILL_NAVY',
    content
)
content = re.sub(
    r'top_bottom = _THIN if col in \(\"G\", \"H\", \"I\", \"J\", \"K\", \"L\", \"M\", \"N\"\) else None',
    r'top_bottom = _THIN if col in (\"G\", \"H\", \"I\", \"J\", \"K\", \"L\", \"M\", \"N\", \"O\", \"P\") else None',
    content
)
content = content.replace('ws.merge_cells(f\"G{row}:J{row}\")', 'ws.merge_cells(f\"G{row}:K{row}\")')
content = content.replace('ws.merge_cells(f\"K{row}:N{row}\")', 'ws.merge_cells(f\"L{row}:P{row}\")')
content = content.replace('_set(ws, f\"K{row}\",', '_set(ws, f\"L{row}\",')
content = content.replace('ws.merge_cells(f\"O{row}:O{sub_row}\")', 'ws.merge_cells(f\"Q{row}:Q{sub_row}\")')
content = content.replace('_set(ws, f\"O{row}\", \"Catatan\"', '_set(ws, f\"Q{row}\", \"Catatan\"')

# replace metric labels loop
content = re.sub(
    r'for label, col in \(\(\"Plafon\", \"G\"\), \(\"Klaim\", \"H\"\), \(\"Dibayar\", \"I\"\), \(\"Saldo\", \"J\"\)\):',
    r'for label, col in ((\"Plafon\", \"G\"), (\"PTA\", \"H\"), (\"Klaim\", \"I\"), (\"Dibayar\", \"J\"), (\"Saldo\", \"K\")):',
    content
)
content = re.sub(
    r'for label, col in \(\(\"Plafon\", \"K\"\), \(\"Klaim\", \"L\"\), \(\"Dibayar\", \"M\"\), \(\"Saldo\", \"N\"\)\):',
    r'for label, col in ((\"Plafon\", \"L\"), (\"PTA\", \"M\"), (\"Klaim\", \"N\"), (\"Dibayar\", \"O\"), (\"Saldo\", \"P\")):',
    content
)

# replace columns=[\"O\"] to columns=[\"Q\"]
content = content.replace('columns=[\"O\"]', 'columns=[\"Q\"]')

with open(r'app\modules\sahabat_etf\report_xlsx.py', 'w', encoding='utf-8') as f:
    f.write(content)
