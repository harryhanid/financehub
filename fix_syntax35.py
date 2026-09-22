import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

with open("C:/Financehub/implement_pdf_scaling.py", "r", encoding="utf-8") as f:
    impl_content = f.read()

# Extract replacement from implement_pdf_scaling.py
match = re.search(r'replacement = """(async function setfExportPdf\(\) \{[\s\S]*?\n\})"""', impl_content)
if match:
    replacement = match.group(1)
    
    # Find setfExportPdf in content
    start_idx = content.find("async function setfExportPdf()")
    if start_idx != -1:
        end_idx = content.find("function", start_idx + 1)
        if end_idx == -1: end_idx = len(content)
        
        # Replace
        content = content[:start_idx] + replacement + "\n\n" + content[end_idx:]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Replaced PDF Export function perfectly!")
    else:
        print("Could not find setfExportPdf in sahabat_etf.js")
else:
    print("Could not extract replacement")
