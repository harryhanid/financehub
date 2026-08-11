import re

with open('app/templates/payment_memo/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Remove the bad clone
p_bad = re.compile(r'(// [^\n]*Advance/ENERGY pillar tables[^\n]*\n.*?\n)(?=(// [^\n]*PA Advance \(ETF PA quarantine-until-realized route\)[^\n]*\n))', re.DOTALL)
m_bad = p_bad.search(c)
if m_bad:
    print("Found bad clone, removing...")
    c = c[:m_bad.start()] + c[m_bad.end():]
else:
    print("Bad clone not found!")

# 2. Add the correct clone
# Look for exactly something containing "─ SETF ─" or similar, just be careful not to match the first dynamic height comment which doesn't have ─ SETF ─
p_good = re.compile(r'(// [^\n]*─ SETF ─[^\n]*\n.*?\n)(?=(// [^\n]*PA Advance \(ETF PA quarantine-until-realized route\)[^\n]*\n))', re.DOTALL)
m_good = p_good.search(c)
if m_good:
    print("Found good SETF block, cloning...")
    setf_js = m_good.group(1)
    energy_js = setf_js.replace('SETF', 'ENERGY').replace('setf', 'energy').replace('Setf', 'Energy')
    c = c[:m_good.end()] + energy_js + c[m_good.end():]
else:
    print("Good SETF block not found! Trying fallback regex...")
    # fallback in case the character is not ─
    p_good2 = re.compile(r'(// [^a-zA-Z0-9\n]*SETF[^a-zA-Z0-9\n]*\n.*?\n)(?=(// [^\n]*PA Advance \(ETF PA quarantine-until-realized route\)[^\n]*\n))', re.DOTALL)
    m_good2 = p_good2.search(c)
    if m_good2:
        print("Found good SETF block (fallback), cloning...")
        setf_js = m_good2.group(1)
        energy_js = setf_js.replace('SETF', 'ENERGY').replace('setf', 'energy').replace('Setf', 'Energy')
        c = c[:m_good2.end()] + energy_js + c[m_good2.end():]
    else:
        print("Fallback also failed!")

with open('app/templates/payment_memo/index.html', 'w', encoding='utf-8') as f:
    f.write(c)
