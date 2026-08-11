import re

with open('templates/payment_memo/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

# HTML clone
p_html = re.compile(r'(  <!-- SETF Tab -->\n.*?\n)(?=  <!-- Advance Tab \(ETF PA quarantine-until-realized route\) -->)', re.DOTALL)
m_html = p_html.search(c)
if m_html:
    setf_html = m_html.group(1)
    energy_html = setf_html.replace('SETF', 'ENERGY').replace('setf', 'energy')
    c = c[:m_html.end()] + energy_html + c[m_html.end():]
    print("Cloned HTML")
else:
    print("Failed to find HTML")

# JS clone
p_js = re.compile(r'(// [^\n]*SETF[^\n]*\n.*?\n)(?=(// [^\n]*PA Advance \(ETF PA quarantine-until-realized route\)[^\n]*\n))', re.DOTALL)
m_js = p_js.search(c)
if m_js:
    setf_js = m_js.group(1)
    energy_js = setf_js.replace('SETF', 'ENERGY').replace('setf', 'energy').replace('Setf', 'Energy')
    c = c[:m_js.end()] + energy_js + c[m_js.end():]
    print("Cloned JS")
else:
    print("Failed to find JS")

with open('templates/payment_memo/index.html', 'w', encoding='utf-8') as f:
    f.write(c)
