import re

with open(r'app\tests\test_sahabat_etf_report_xlsx.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('assert ws["O1"].value == "(Rp, Dalam Jutaan)"', 'assert ws["Q1"].value == "(Rp, Dalam Jutaan)"')
content = content.replace('assert ws["K3"].value == "S/D TAHUN 2026"', 'assert ws["L3"].value == "S/D TAHUN 2026"')
content = content.replace('assert ws["O3"].value == "Catatan"', 'assert ws["Q3"].value == "Catatan"')

# Headers in G4-K4
content = content.replace('assert ws["H4"].value == "Klaim"', 'assert ws["H4"].value == "PTA"\n    assert ws["I4"].value == "Klaim"')
content = content.replace('assert ws["I4"].value == "Dibayar"', 'assert ws["J4"].value == "Dibayar"')
content = content.replace('assert ws["J4"].value == "Saldo"', 'assert ws["K4"].value == "Saldo"')

# cum.plafon in K -> L
content = content.replace('assert values[richard_row]["K"] == 90.0', 'assert values[richard_row]["L"] == 90.0')

with open(r'app\tests\test_sahabat_etf_report_xlsx.py', 'w', encoding='utf-8') as f:
    f.write(content)
