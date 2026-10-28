with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Replace colspans for empty messages
text = text.replace('Belum ada PAM record AGRI.</td></tr>\';', 'Belum ada PAM record AGRI.</td></tr>\';').replace('colspan="28"', 'colspan="29"')
# Wait, replacing `colspan="28"` globally might replace others.
# Let's be precise.

changes = [
    ("colspan=\"28\"", "Belum ada PAM record AGRI", "colspan=\"29\""),
    ("colspan=\"27\"", "Belum ada data APP", "colspan=\"28\""),
    ("colspan=\"26\"", "Belum ada data LAND", "colspan=\"27\""),
    ("colspan=\"17\"", "Belum ada data ENERGY", "colspan=\"18\""),
    ("colspan=\"17\"", "Belum ada data SETF", "colspan=\"18\""),
    ("colspan=\"28\"", "Belum ada data SMT", "colspan=\"29\"")
]

lines = text.split('\n')
for i, line in enumerate(lines):
    for old_col, trigger, new_col in changes:
        if trigger in line and old_col in line:
            lines[i] = line.replace(old_col, new_col)

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write('\n'.join(lines))
