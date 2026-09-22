import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove strokeText for the grouped sublabels (yBaseline + 4)
content = re.sub(r'ctx\.strokeText\(lbl,\s*meta\.data\[j\]\.x,\s*yBaseline \+ 4\);\s*', '', content)

# 2. Remove strokeText for the stacked sublabels (yBaseline + 14)
content = re.sub(r'ctx\.strokeText\(lbl,\s*anyMeta\.x,\s*yBaseline \+ 14\);\s*', '', content)

# 3. Double check label[0] and label[1] in case my previous replace failed
content = re.sub(r'ctx\.strokeText\(label\[0\],\s*xPos,\s*yPos\);\s*', '', content)
content = re.sub(r'ctx\.strokeText\(label\[1\],\s*xPos,\s*yPos \+ 14\);\s*', '', content)


with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Removed strokeText using regex!")
