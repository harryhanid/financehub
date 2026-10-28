import re
with open("rendered.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "replace(" in line and "/" in line:
        if re.search(r'replace\s*\(\s*/[^/]*/[gimuy]*\s*,\s*[\'"].*?[\'"]\s*\)', line):
            pass
        else:
            print(f"Suspicious regex at Line {i+1}: {line.strip()}")
