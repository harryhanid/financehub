file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

if lines[577].strip() == "}":
    print("Deleting extra } at line 578")
    del lines[577]
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
else:
    print("Line 578 is not just a }. It is: " + lines[577])
