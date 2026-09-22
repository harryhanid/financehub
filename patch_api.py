import re

file_path = "C:/Financehub/app/modules/sahabat_etf/routes.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'return jsonify\(\{"ok": True, "data": build_report_data\(_cid\(\), int\(year_param\), month, pillars\)\}\)'
repl = """try:
        data = build_report_data(_cid(), int(year_param), month, pillars)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        import traceback
        with open("C:/Financehub/last_500_error.txt", "w") as errf:
            errf.write(traceback.format_exc())
        return jsonify({"ok": False, "pesan": str(e)}), 500"""

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Monkey-patched api_report!")
