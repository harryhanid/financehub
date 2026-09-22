import re
import os

file_path = "C:/Financehub/app/templates/sahabat_etf/_panel.html"
if os.path.exists(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    target = r'<div class="budget-card" id="setf-alert-card" style="display:none">\s*<h3>Anggota Over-Budget</h3>\s*<ul id="setf-alert-list"></ul>\s*</div>'
    replacement = """<div class="budget-card" id="setf-exec-summary-card">
        <h3>Executive Summary</h3>
        <p id="setf-exec-summary-text" style="line-height: 1.6; margin-top: 0.5rem;"></p>
      </div>"""
    
    new_content = re.sub(target, replacement, content)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("HTML updated.")
else:
    print("File not found.")
