import re

with open("C:/Financehub/app/modules/beasiswa/routes.py", "r", encoding="utf-8") as f:
    content = f.read()

old_render = """            return render_template("sahabat_etf/public_index.html")"""
new_render = """            return render_template(
                "sahabat_etf/public_index.html",
                available_years=get_available_years(_cid()) if not _wrong_company() else [],
                available_pillars=get_available_pillars(_cid()) if not _wrong_company() else []
            )"""
content = content.replace(old_render, new_render)

with open("C:/Financehub/app/modules/beasiswa/routes.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated public render context!")
