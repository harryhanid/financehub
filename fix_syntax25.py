file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

import re

# Let's find exactly the line where `const setfStackTotalPlugin = {` starts!
start = -1
for i, line in enumerate(lines):
    if "const setfStackTotalPlugin = {" in line:
        start = i
        break

if start != -1:
    end = -1
    for i in range(start, len(lines)):
        if "};" in lines[i]:
            end = i
            break
    print(f"Deleting from {start} to {end}")
    new_lines = lines[:start] + lines[end+1:]
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
else:
    print("Not found")
