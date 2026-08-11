import re

def patch_etf_pa():
    path = 'app/templates/etf_payment_application/index.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    # 1. Main tabs block
    c = c.replace(
        "('sml','LAND'),('setf','SETF'),('energy','ENERGY & FINANCE')]",
        "('sml','LAND'),('energy','EFIN'),('setf','SETF')]"
    )

    # 2. Select Jenis PA block
    c = c.replace(
        "<option value=\"setf\">SETF</option>\n      <option value=\"energy\">ENERGY & FINANCE</option>",
        "<option value=\"energy\">EFIN</option>\n      <option value=\"setf\">SETF</option>"
    )

    # 3. _PILLAR_STYLE
    c = c.replace(
        "setf:   'background:#cffafe;color:#164e63;border:1px solid #0891b2',\n    energy: 'background:#fce7f3;color:#9d174d;border:1px solid #be185d',",
        "energy: 'background:#fce7f3;color:#9d174d;border:1px solid #be185d',\n    setf:   'background:#cffafe;color:#164e63;border:1px solid #0891b2',"
    )
    # The other _PILLAR_STYLE in advance tab
    c = c.replace(
        "setf:   'background:#cffafe;color:#164e63;border:1px solid #0891b2',\n    energy: 'background:#fce7f3;color:#9d174d;border:1px solid #be185d',",
        "energy: 'background:#fce7f3;color:#9d174d;border:1px solid #be185d',\n    setf:   'background:#cffafe;color:#164e63;border:1px solid #0891b2',"
    )

    # 4. _PILLAR_LABEL
    c = c.replace("sml:'LAND', setf:'SETF', energy:'ENERGY & FINANCE'", "sml:'LAND', energy:'EFIN', setf:'SETF'")
    c = c.replace("sml:'LAND', setf:'SETF', energy:'ENERGY & FINANCE'", "sml:'LAND', energy:'EFIN', setf:'SETF'") # in case of two

    # 5. _TAB_LABEL
    c = c.replace("sml: 'LAND', setf: 'SETF', energy: 'ENERGY & FINANCE'", "sml: 'LAND', energy: 'EFIN', setf: 'SETF'")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)

def patch_pam():
    path = 'app/templates/payment_memo/index.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    # 1. Tab buttons
    c = c.replace(
        '<button class="tab-btn" data-tab="tab-setf" onclick="loadSETF()">SETF</button>\n  <button class="tab-btn" data-tab="tab-energy" onclick="loadENERGY()">ENERGY &amp; FINANCE</button>',
        '<button class="tab-btn" data-tab="tab-energy" onclick="loadENERGY()">EFIN</button>\n  <button class="tab-btn" data-tab="tab-setf" onclick="loadSETF()">SETF</button>'
    )
    c = c.replace(
        '<button class="tab-btn" data-tab="tab-setf" onclick="loadSETF()">SETF</button>\n  <button class="tab-btn" data-tab="tab-energy" onclick="loadENERGY()">ENERGY & FINANCE</button>',
        '<button class="tab-btn" data-tab="tab-energy" onclick="loadENERGY()">EFIN</button>\n  <button class="tab-btn" data-tab="tab-setf" onclick="loadSETF()">SETF</button>'
    )
    # wait, the earlier patch wrote: 
    # '<button class="tab-btn" data-tab="tab-setf" onclick="loadSETF()">SETF</button>\n  <button class="tab-btn" data-tab="tab-energy" onclick="loadENERGY()">ENERGY &amp; FINANCE</button>'
    
    # 2. ipay-type
    c = c.replace(
        '<option value="setf">SETF</option>\n          <option value="energy">ENERGY &amp; FINANCE</option>',
        '<option value="energy">EFIN</option>\n          <option value="setf">SETF</option>'
    )
    c = c.replace(
        '<option value="setf">SETF</option>\n          <option value="energy">ENERGY & FINANCE</option>',
        '<option value="energy">EFIN</option>\n          <option value="setf">SETF</option>'
    )
    
    # 3. vendor pillar dropdowns
    c = c.replace(
        '<option value="SETF">SETF</option>\n        <option value="ENERGY">ENERGY &amp; FINANCE</option>',
        '<option value="ENERGY">EFIN</option>\n        <option value="SETF">SETF</option>'
    )
    c = c.replace(
        '<option value="SETF">SETF</option>\n        <option value="ENERGY">ENERGY & FINANCE</option>',
        '<option value="ENERGY">EFIN</option>\n        <option value="SETF">SETF</option>'
    )
    
    # 4. _PILLAR_STYLE
    c = c.replace(
        "SETF:   'background:#cffafe;color:#164e63;border:1px solid #0891b2',\n    ENERGY: 'background:#fce7f3;color:#9d174d;border:1px solid #be185d',",
        "ENERGY: 'background:#fce7f3;color:#9d174d;border:1px solid #be185d',\n    SETF:   'background:#cffafe;color:#164e63;border:1px solid #0891b2',"
    )
    
    # 5. edit PAM modal dropdowns
    c = c.replace("['AGRI', 'APP', 'LAND', 'SETF', 'ENERGY']", "['AGRI', 'APP', 'LAND', 'ENERGY', 'SETF']")
    
    # 6. _PAM_RE
    c = c.replace("(ETF|APP|LAND|SETF|SMT|ENERGY)", "(ETF|APP|LAND|ENERGY|SETF|SMT)")
    
    # 7. _IPAY_LABEL
    c = c.replace("setf: 'SETF', energy: 'ENERGY & FINANCE'", "energy: 'EFIN', setf: 'SETF'")
    
    # 8. Prefix
    c = c.replace("SETF: 'setf', ENERGY: 'energy'", "ENERGY: 'energy', SETF: 'setf'")
    
    # 9. tab nav mapping
    c = c.replace(
        "SETF: ['tab-setf',  'setf-search'],\n    ENERGY: ['tab-energy', 'energy-search'],",
        "ENERGY: ['tab-energy', 'energy-search'],\n    SETF: ['tab-setf',  'setf-search'],"
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)

def patch_tests():
    # Update tests testing for ENERGY & FINANCE to EFIN
    import glob
    for path in glob.glob('app/tests/*.py'):
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()
        if 'ENERGY &amp; FINANCE' in c or 'ENERGY & FINANCE' in c:
            c = c.replace('ENERGY &amp; FINANCE', 'EFIN').replace('ENERGY & FINANCE', 'EFIN')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(c)

patch_etf_pa()
patch_pam()
patch_tests()
print("Done!")
