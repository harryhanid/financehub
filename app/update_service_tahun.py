path = r"C:\Financehub\app\modules\sponsorship\service.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
    '''            query += f" AND (strftime('%Y', tanggal_form_sponsor) IN ({placeholders}) OR strftime('%Y', tanggal_payment) IN ({placeholders}))"
            params.extend(years)
            params.extend(years)''',
    '''            query += f" AND strftime('%Y', tanggal_form_sponsor) IN ({placeholders})"
            params.extend(years)'''
).replace(
    '''            query += " AND (strftime('%Y', tanggal_form_sponsor) = ? OR strftime('%Y', tanggal_payment) = ?)"
            params.extend([str(years), str(years)])''',
    '''            query += " AND strftime('%Y', tanggal_form_sponsor) = ?"
            params.extend([str(years)])'''
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done service.py")
