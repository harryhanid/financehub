import re
file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r"let color = setfColorForCategory\(lbl\);"
repl = """let color = setfColorForCategory(lbl);
        if (canvasId.includes("pillar")) {
            if (lbl === "AGRI") color = "#10b981";
            else if (lbl === "APP") color = "#3b82f6";
            else if (lbl === "FINANCE") color = "#f59e0b";
            else if (lbl === "SETF") color = "#8b5cf6";
            else color = "#64748b";
        }"""

new_content = content.replace(target, repl)
with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)
print("Added hardcoded colors to BVR chart!")
