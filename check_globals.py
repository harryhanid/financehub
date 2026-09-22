file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

in_func = False
braces = 0

for i, line in enumerate(lines):
    if "function " in line and "{" in line:
        # Simplistic, just to catch major blocks
        braces += line.count("{") - line.count("}")
        in_func = braces > 0
    elif in_func:
        braces += line.count("{") - line.count("}")
        in_func = braces > 0
    else:
        if "const " in line or "let " in line or "var " in line:
            if not line.startswith("const setf") and not line.startswith("let setf") and not line.startswith("var setf") and "Chart(" not in line and "plugins: " not in line and "document." not in line:
                print(f"Line {i+1}: {line.strip()}")
