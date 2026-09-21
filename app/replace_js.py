import re

with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

new_func = """function expandPathToName(node, searchName) {
  let found = false;
  let isTarget = false;

  if (node.name.toLowerCase().includes(searchName)) {
    found = true;
    isTarget = true;
  }
  if (node.partners && node.partners.some(p => p.name.toLowerCase().includes(searchName))) {
    found = true;
    isTarget = true;
  }

  let matchedChildren = [];
  let neededPartnerIds = new Set();

  if (node.children && node.children.length > 0) {
    node.children.forEach(c => {
      if (expandPathToName(c, searchName)) {
        matchedChildren.push(c);
        if (c.parent_partner_id) {
          neededPartnerIds.add(c.parent_partner_id);
        }
        found = true;
      }
    });
  }

  if (found && !isTarget) {
    node.children = matchedChildren;
    if (node.partners) {
       let arr = Array.from(neededPartnerIds);
       node.partners = node.partners.filter(p => arr.includes(p.id));
    }
    node.collapsed = false;
  } else if (isTarget) {
    node.collapsed = false; 
    node.itemStyle = { borderColor: '#ef4444', borderWidth: 3 };
    node.label = { backgroundColor: '#fee2e2', borderColor: '#ef4444' };
  } else {
    node.collapsed = true;
  }
  return found;
}"""

content = re.sub(r'function expandPathToName\(node, searchName\).*?return found;\s*}', new_func, content, flags=re.DOTALL)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)

print("Replaced!")
