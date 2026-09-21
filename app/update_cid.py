import re

with open("C:/Financehub/app/modules/sahabat_etf/routes.py", "r", encoding="utf-8") as f:
    content = f.read()

old_cid = """def _cid():
    return session.get("company_id")"""

new_cid = """def _cid():
    if session.get("public_sahabat_access"):
        return 2
    return session.get("company_id")"""

content = content.replace(old_cid, new_cid)

with open("C:/Financehub/app/modules/sahabat_etf/routes.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated _cid() for public access!")
