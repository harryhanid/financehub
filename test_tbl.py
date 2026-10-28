with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

for tbl in ['pam-table', 'fiori-table', 'sml-table', 'energy-table', 'setf-table']:
    for i, line in enumerate(text.splitlines()):
        if f'id="{tbl}"' in line:
            print(f'{tbl} at line {i+1}')
