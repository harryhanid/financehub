import re

file_path = r'C:\Financehub\app\templates\payment_memo\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

def replace_in_tbody(tbody_id, prefix, colspan, content):
    pattern = r"(const tbody\s*=\s*document\.getElementById\('" + tbody_id + r"'\);.*?tbody\.innerHTML = data\.rows\.map\(\(r, i\) => `\s*)<tr[^>]*>\s*<td([^>]*)>(.*?\$\{esc\(r\.pam_no\)\}.*?)</td>"
    def repl(m):
        return m.group(1) + f'<tr class="{prefix}-row" style="background:${{i % 2 === 0 ? \'#fff\' : \'#f8fafc\'}};cursor:pointer" onclick="_toggleEtfExpandGeneric(event, this, ${{r.id}}, {colspan}, \'{prefix}\')">\n      <td' + m.group(2) + '><span style="display:inline-block;margin-right:4px;color:#3b82f6">&#9658;</span>' + m.group(3) + '</td>'
    
    new_content, count = re.subn(pattern, repl, content, flags=re.DOTALL)
    print(f"Replaced {tbody_id}: {count}")
    return new_content

content = replace_in_tbody('sml-tbody', 'sml', 25, content)
content = replace_in_tbody('setf-tbody', 'setf', 16, content)

fiori_pattern = r"(const tbody\s*=\s*document\.getElementById\('fiori-tbody'\);.*?tbody\.innerHTML = data\.rows\.map\(\(r, i\) => `\s*)<tr class=\"fiori-row\" style=\"background:\$\{i \% 2 === 0 \? '#fff' : '#f8fafc'\};(?:\w|\s|:|;|\"|')*\">\s*<td class=\"f0\"([^>]*)><input type=\"checkbox\" class=\"fiori-cb\"([^>]*)></td>\s*<td class=\"f1\"([^>]*)>(.*?\$\{esc\(r\.pam_no\)\}.*?)</td>"
def fiori_repl(m):
    return m.group(1) + f'<tr class="fiori-row" style="background:${{i % 2 === 0 ? \'#fff\' : \'#f8fafc\'}};cursor:pointer" onclick="_toggleEtfExpandGeneric(event, this, ${{r.id}}, 26, \'fiori\')">\n      <td class="f0"' + m.group(2) + '><input type="checkbox" class="fiori-cb"' + m.group(3) + '></td>\n      <td class="f1"' + m.group(4) + '><span style="display:inline-block;margin-right:4px;color:#3b82f6">&#9658;</span>' + m.group(5) + '</td>'
content, count = re.subn(fiori_pattern, fiori_repl, content, flags=re.DOTALL)
print(f"Replaced fiori-tbody: {count}")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
