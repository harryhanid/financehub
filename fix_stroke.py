import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove stroke for GroupedSublabelPlugin
content = content.replace("ctx.strokeText(lbl, meta.data[j].x, yBaseline + 4);\n              ctx.fillText(lbl, meta.data[j].x, yBaseline + 4);", "ctx.fillText(lbl, meta.data[j].x, yBaseline + 4);")

# 2. Remove stroke for array labels (if any)
content = content.replace("ctx.strokeText(label[0], xPos, yPos);\n              ctx.fillText(label[0], xPos, yPos);", "ctx.fillText(label[0], xPos, yPos);")
content = content.replace("ctx.strokeText(label[1], xPos, yPos + 14);\n              ctx.fillText(label[1], xPos, yPos + 14);", "ctx.fillText(label[1], xPos, yPos + 14);")

# 5. Remove stroke for StackTotalPlugin sublabel (Bgt/Act)
content = content.replace("ctx.strokeText(lbl, anyMeta.x, yBaseline + 14);\n              ctx.fillText(lbl, anyMeta.x, yBaseline + 14);", "ctx.fillText(lbl, anyMeta.x, yBaseline + 14);")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Removed bad strokeText!")
