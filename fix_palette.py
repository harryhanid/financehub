import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace palette
target_palette = r'const SETF_PALETTE = \["#6366f1", "#818cf8", "#f97316", "#06b6d4", "#10b981", "#f59e0b"\];'
replacement_palette = 'const SETF_PALETTE = ["#6366f1", "#14b8a6", "#f97316", "#ec4899", "#10b981", "#f59e0b"];'
content = re.sub(target_palette, replacement_palette, content)

# Replace shapes array
target_shapes = r"const shapes = \['diagonal', 'weave', 'dot', 'square', 'zigzag', 'triangle', 'cross'\];"
replacement_shapes = "const shapes = ['dot', 'diagonal-right-left', 'square', 'zigzag', 'triangle', 'weave', 'cross'];"
content = re.sub(target_shapes, replacement_shapes, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
