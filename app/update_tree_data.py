import re

with open("C:/Financehub/app/modules/sahabat_etf/routes.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace SELECT query
old_query = "SELECT code, nama, group_setf FROM siswa WHERE program='Sahabat ETF' AND group_setf != ''"
new_query = "SELECT code, nama, group_setf, tanggal_lahir, catatan FROM siswa WHERE program='Sahabat ETF' AND group_setf != ''"
content = content.replace(old_query, new_query)

# Replace the loop unpacking
old_loop = "for code, nama, g in rows:"
new_loop = "for code, nama, g, tgl_lahir, catatan in rows:"
content = content.replace(old_loop, new_loop)

# Replace bloodlines and partners assignments
old_b1 = "bloodlines[g] = {'id': g, 'code': code, 'name': nama, 'partners': [], 'children': []}"
new_b1 = "bloodlines[g] = {'id': g, 'code': code, 'name': nama, 'partners': [], 'children': [], 'tanggal_lahir': tgl_lahir, 'catatan': catatan}"
content = content.replace(old_b1, new_b1)

old_p1 = "partners[g] = {'id': g, 'name': nama, 'code': code, 'base': base}"
new_p1 = "partners[g] = {'id': g, 'name': nama, 'code': code, 'base': base, 'tanggal_lahir': tgl_lahir, 'catatan': catatan}"
content = content.replace(old_p1, new_p1)

with open("C:/Financehub/app/modules/sahabat_etf/routes.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated backend for tooltip data")
