import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

old_partner = """                    let pCode = p.id ? p.id.split('.').pop() : '';
                    let pName = p.name || '';
                    if (pCode && pCode !== 'A' && pCode !== 'B') {
                        pName = pName + ' (' + pCode + ')';
                    }
                    pName = pName + ' (Partner)';"""

new_partner = """                    let pCode = p.id ? p.id.split('.').pop().toUpperCase() : '';
                    let pName = p.name || '';
                    let partnerSuffix = 'Partner';
                    if (pCode && pCode !== 'A' && pCode !== 'B' && pCode !== '') {
                        // If it's a numeric code or something else, wait.
                        // Actually the user wants a,b,c to become Partner A, Partner B.
                        // So any pCode can just be appended.
                        partnerSuffix = 'Partner ' + pCode;
                    } else if (pCode === 'A' || pCode === 'B') {
                        partnerSuffix = 'Partner ' + pCode;
                    }
                    pName = pName + ' (' + partnerSuffix + ')';"""

# Let's simplify new_partner
new_partner = """                    let pCode = p.id ? p.id.split('.').pop().toUpperCase() : '';
                    let pName = p.name || '';
                    let partnerSuffix = pCode ? 'Partner ' + pCode : 'Partner';
                    pName = pName + ' (' + partnerSuffix + ')';"""

if old_partner in content:
    content = content.replace(old_partner, new_partner)
    with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Replaced partner name logic successfully!")
else:
    print("Could not find old partner logic!")
