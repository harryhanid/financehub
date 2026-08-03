path = r"C:\Financehub\app\modules\sponsorship\exports.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
    '_COLUMN_LABELS = ["NO", "LEMBAGA / PERORANGAN", "PERIHAL", "APP", "AGRI", "ENERGY & FINANCE", "PROPERTY", "TOTAL"]',
    '_COLUMN_LABELS = ["NO", "LEMBAGA / PERORANGAN", "PERIHAL", "APP", "ENERGY", "PROPERTY", "AGRI", "TOTAL"]'
)

# Reorder cell.fill mapping
c = c.replace(
    'elif col == 5: cell.fill = APP_FILL\n            elif col == 6: cell.fill = AGRI_FILL\n            elif col == 7: cell.fill = EF_FILL\n            elif col == 8: cell.fill = PROP_FILL',
    'elif col == 5: cell.fill = APP_FILL\n            elif col == 6: cell.fill = EF_FILL\n            elif col == 7: cell.fill = PROP_FILL\n            elif col == 8: cell.fill = AGRI_FILL'
)

# Reorder data appending for section rows
c = c.replace(
    'r["app_amount"], r["agri_amount"], r["energy_finance_amount"], r["property_amount"], r["total"]',
    'r["app_amount"], r["energy_finance_amount"], r["property_amount"], r["agri_amount"], r["total"]'
)

# Reorder data appending for section subtotals
c = c.replace(
    'sub["app_amount"], sub["agri_amount"], sub["energy_finance_amount"], sub["property_amount"], sub["total"]',
    'sub["app_amount"], sub["energy_finance_amount"], sub["property_amount"], sub["agri_amount"], sub["total"]'
)

# Reorder data appending for grand totals
c = c.replace(
    'gt["app_amount"], gt["agri_amount"], gt["energy_finance_amount"], gt["property_amount"], gt["total"]',
    'gt["app_amount"], gt["energy_finance_amount"], gt["property_amount"], gt["agri_amount"], gt["total"]'
)

# Reorder data appending for percentages
c = c.replace(
    'f"{pct[\'app_amount\']}%", f"{pct[\'agri_amount\']}%", f"{pct[\'energy_finance_amount\']}%", f"{pct[\'property_amount\']}%", ""',
    'f"{pct[\'app_amount\']}%", f"{pct[\'energy_finance_amount\']}%", f"{pct[\'property_amount\']}%", f"{pct[\'agri_amount\']}%", ""'
)


with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done exports.py")
