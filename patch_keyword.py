import os

service_path = r'C:\Financehub\app\modules\sponsorship\service.py'
with open(service_path, 'r', encoding='utf-8') as f:
    service_content = f.read()

search_str = '''    if filters.get("status"):
        query += " AND status = ?"
        params.append(filters["status"])'''

replace_str = '''    if filters.get("keyword"):
        kw = f"%{filters['keyword']}%"
        query += """ AND (
            status LIKE ? OR
            cat LIKE ? OR
            description LIKE ? OR
            cat1 LIKE ? OR
            cat2 LIKE ? OR
            cat3 LIKE ? OR
            lembaga_perorangan LIKE ? OR
            perihal LIKE ? OR
            reff LIKE ?
        )"""
        params.extend([kw] * 9)'''

if search_str in service_content:
    service_content = service_content.replace(search_str, replace_str)
    with open(service_path, 'w', encoding='utf-8') as f:
        f.write(service_content)
    print("service.py patched")
else:
    print("search_str not found in service.py")

data_html_path = r'C:\Financehub\app\templates\sponsorship\data.html'
with open(data_html_path, 'r', encoding='utf-8') as f:
    data_html = f.read()

search_str2 = '''<input type="text" name="status" placeholder="Filter Status..." value="{{ filters.status or '' }}">'''
replace_str2 = '''<input type="text" name="keyword" placeholder="Cari (keyword)..." value="{{ filters.keyword or '' }}">'''

if search_str2 in data_html:
    data_html = data_html.replace(search_str2, replace_str2)
    with open(data_html_path, 'w', encoding='utf-8') as f:
        f.write(data_html)
    print("data.html patched")
else:
    print("search_str2 not found in data.html")
