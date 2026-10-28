with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/system_flowchart.md", "r", encoding="utf-8") as f:
    text = f.read()

# Replace (Sistem) with (Flow)
text = text.replace("(Sistem)", "(Flow)")
text = text.replace("Proses Otomatis oleh Sistem", "Proses Otomatis oleh Flow")

# Remove direction TB to fix overlap
text = text.replace("    direction TB\n", "")

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/system_flowchart.md", "w", encoding="utf-8") as f:
    f.write(text)

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.html", "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace("(Sistem)", "(Flow)")
html = html.replace("Proses Sistem Otomatis", "Proses Flow Otomatis")
html = html.replace("    direction TB\n", "")

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.html", "w", encoding="utf-8") as f:
    f.write(html)
