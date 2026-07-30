import re

file_path = r'C:\Financehub\app\templates\payment_memo\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace SML
sml_pattern = r'<tr style="background:\$\{i \% 2 === 0 \? \'#fff\' : \'#f8fafc\'\};">\s*<td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap">\$\{esc\(r\.pam_no\)\}</td>'
sml_repl = '''<tr class="sml-row" style="background:;cursor:pointer" onclick="_toggleEtfExpandGeneric(event, this, , 25, 'sml')">
      <td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap">
        <span style="display:inline-block;margin-right:4px;color:#3b82f6">&#9658;</span>
      </td>'''
content, count = re.subn(sml_pattern, sml_repl, content)
print(f"SML replaced: {count}")

# Replace SETF
# Wait, SETF also uses the EXACT same string as SML initially. 
# But since I did re.subn, it probably replaced both SML and SETF!
# Let's see if the count is 2.
