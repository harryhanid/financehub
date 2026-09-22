file_path = "C:/Financehub/app/modules/sahabat_etf/routes.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

import re
content = re.sub(r'def api_pohon\(\):[\s\S]*?diagram2": build_pohon_group_data\(_cid\(\), report_year, month, pillars\)\n\s*\}\n\s*\}\)', """def api_pohon():
    years = request.args.getlist("years[]")
    if not years:
        years_csv = request.args.get("years", "")
        if years_csv:
            years = [y.strip() for y in years_csv.split(",")]

    parsed_years = []
    for y in years:
        if y.lower() in ("all", "semua"):
            parsed_years = None
            break
        elif y.isdigit():
            parsed_years.append(int(y))
    
    if parsed_years is not None and not parsed_years:
        parsed_years = None

    month, pillars = _parse_report_filters()
    from .service import build_pohon_data, build_pohon_group_data
    return jsonify({
        "ok": True,
        "data": {
            "diagram1": build_pohon_data(_cid(), parsed_years, pillars),
            "diagram2": build_pohon_group_data(_cid(), parsed_years, pillars)
        }
    })""", content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated routes.py")
