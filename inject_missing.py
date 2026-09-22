import re

with open('pristine_sahabat.js', 'r', encoding='utf-8') as f:
    p_content = f.read()

with open('app/static/js/sahabat_etf.js', 'r', encoding='utf-8') as f:
    t_content = f.read()

def get_funcs(c):
    return set(re.findall(r'function\s+([a-zA-Z0-9_]+)\s*\(', c))

p_funcs = get_funcs(p_content)
t_funcs = get_funcs(t_content)
missing_funcs = p_funcs - t_funcs

extracted_code = ""

constants = """
const SETF_BULAN_LABEL = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
const SETF_PALETTE = ["#6366f1", "#818cf8", "#f97316", "#06b6d4", "#10b981", "#f59e0b", "#a855f7", "#ec4899", "#ef4444", "#8b5cf6"];
const setfCategoryColorMap = {};
"""
if "SETF_BULAN_LABEL" not in t_content:
    extracted_code += constants + "\n"

for func_name in missing_funcs:
    start_idx = p_content.find(f"function {func_name}(")
    if start_idx == -1:
        start_idx = p_content.find(f"function {func_name} (")
        
    if start_idx != -1:
        brace_count = 0
        in_func = False
        end_idx = start_idx
        while end_idx < len(p_content):
            if p_content[end_idx] == '{':
                brace_count += 1
                in_func = True
            elif p_content[end_idx] == '}':
                brace_count -= 1
            
            end_idx += 1
            if in_func and brace_count == 0:
                break
        func_code = p_content[start_idx:end_idx]
        extracted_code += func_code + "\n\n"

insert_point = "let setfCharts = {};"
t_idx = t_content.find(insert_point)
if t_idx != -1:
    new_content = t_content[:t_idx + len(insert_point)] + "\n\n" + extracted_code + t_content[t_idx + len(insert_point):]
    with open('app/static/js/sahabat_etf.js', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Successfully injected {len(missing_funcs)} missing functions.")
else:
    print("Could not find insertion point.")
