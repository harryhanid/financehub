import os

routes_path = r'C:\Financehub\app\modules\sponsorship\routes.py'
with open(routes_path, 'r', encoding='utf-8') as f:
    routes_content = f.read()

search_str = 'for key in ("cat1", "cat2", "cat4", "description", "status"):'
replace_str = 'for key in ("cat1", "cat2", "cat4", "description", "keyword"):'

if search_str in routes_content:
    routes_content = routes_content.replace(search_str, replace_str)
    with open(routes_path, 'w', encoding='utf-8') as f:
        f.write(routes_content)
    print("routes.py patched")
else:
    print("search_str not found in routes.py")
