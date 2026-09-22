import json

with open('app/modules/payment_memo/routes.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('def ipay_save_pa():'):
        new_lines.append(line)
        new_lines.append('''    if request.is_json:
        data = request.get_json(force=True) or {}
    else:
        import json
        data = json.loads(request.form.get("data", "{}"))\n''')
    elif line.startswith('def ipay_save_klaim():') or line.startswith('def ipay_save_others():') or line.startswith('def ipay_save_smt_lines():') or line.startswith('def update_pam_record_route(pam_id):'):
        new_lines.append(line)
        new_lines.append('''    if request.is_json:
        data = request.get_json(force=True) or {}
    else:
        import json
        data = json.loads(request.form.get("data", "{}"))\n''')
    elif 'data         = request.get_json(force=True) or {}' in line:
        continue
    elif 'data     = request.get_json(force=True) or {}' in line:
        continue
    else:
        new_lines.append(line)

with open('app/modules/payment_memo/routes.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

