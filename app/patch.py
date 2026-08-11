import re

with open('templates/payment_memo/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. badge-setf
c = c.replace('.badge-setf  { background: #cffafe; color: #164e63; border: 1px solid #0891b2; border-radius: .25rem; padding: .1rem .35rem; }',
              '.badge-setf  { background: #cffafe; color: #164e63; border: 1px solid #0891b2; border-radius: .25rem; padding: .1rem .35rem; }\n.badge-energy { background: #fce7f3; color: #9d174d; border: 1px solid #be185d; border-radius: .25rem; padding: .1rem .35rem; }')

# 2. tab button
c = c.replace('<button class="tab-btn" data-tab="tab-setf" onclick="loadSETF()">SETF</button>',
              '<button class="tab-btn" data-tab="tab-setf" onclick="loadSETF()">SETF</button>\n  <button class="tab-btn" data-tab="tab-energy" onclick="loadENERGY()">ENERGY &amp; FINANCE</button>')

# 3. ipay-type (only the first occurrence in the PAM page, wait, ipay-type is only once in PAM page)
c = c.replace('<option value="setf">SETF</option>',
              '<option value="setf">SETF</option>\n          <option value="energy">ENERGY &amp; FINANCE</option>', 1)

# 4. f-vendor-pillar
c = c.replace('<option value="SETF">SETF</option>',
              '<option value="SETF">SETF</option>\n        <option value="ENERGY">ENERGY &amp; FINANCE</option>')

# 5. _PILLAR_STYLE
c = c.replace("SETF:   'background:#cffafe;color:#164e63;border:1px solid #0891b2',",
              "SETF:   'background:#cffafe;color:#164e63;border:1px solid #0891b2',\n    ENERGY: 'background:#fce7f3;color:#9d174d;border:1px solid #be185d',")

# 6. map(p =>
c = c.replace("['AGRI', 'APP', 'LAND', 'SETF'].map", "['AGRI', 'APP', 'LAND', 'SETF', 'ENERGY'].map")

# 7. _PAM_RE
c = c.replace("/^PAM-\d{3}-(ETF|APP|LAND|SETF|SMT)-\d{2}-\d{4}$/", "/^PAM-\d{3}-(ETF|APP|LAND|SETF|SMT|ENERGY)-\d{2}-\d{4}$/")

# 8. _IPAY_LABEL
c = c.replace("setf: 'SETF', smt: 'SMT'", "setf: 'SETF', energy: 'ENERGY & FINANCE', smt: 'SMT'")

# 9. prefix map
c = c.replace("SETF: 'setf', SMT: 'smt'", "SETF: 'setf', ENERGY: 'energy', SMT: 'smt'")

# 10. tab nav map
c = c.replace("SETF: ['tab-setf',  'setf-search'],", "SETF: ['tab-setf',  'setf-search'],\n    ENERGY: ['tab-energy', 'energy-search'],")

with open('templates/payment_memo/index.html', 'w', encoding='utf-8') as f:
    f.write(c)

print("Patched!")
