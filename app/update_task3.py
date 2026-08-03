path = r"C:\Financehub\app\templates\payment_memo\index.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

for tid in ["tab-draft-pay", "tab-pam", "tab-fiori", "tab-sml", "tab-smt", "tab-advance", "tab-setf", "tab-pa-advance", "tab-vendors"]:
    c = c.replace(f'<div class="tab-panel" id="{tid}">', f'<div class="tab-panel" id="{tid}" data-full-bleed="true">')

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("task 3 done")
