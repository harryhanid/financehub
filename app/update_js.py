import re

with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add assignGenerations
inject_gen = """
function assignGenerations(node, depth) {
  if (depth > 0) {
    node.genLabel = "Gen " + depth;
  } else {
    node.genLabel = "";
  }
  if (node.children) {
    node.children.forEach(c => assignGenerations(c, depth + 1));
  }
}
"""
if "assignGenerations" not in content:
    content = content.replace("async function initTreeQuery() {", inject_gen + "\nasync function initTreeQuery() {")

# 2. Call assignGenerations in initTreeQuery
if "assignGenerations(treeRawData, 0);" not in content:
    content = content.replace("const dl = document.getElementById(\"tree-search-list\");", "assignGenerations(treeRawData, 0);\n    const dl = document.getElementById(\"tree-search-list\");")

# 3. Update formatter
new_formatter = """          formatter: function(params) {
            let n = params.data.name;
            let gen = params.data.genLabel ? `{gen|[${params.data.genLabel}]} ` : '';
            let lines = [`${gen}{main|${n}}`];
            let ps = params.data.partners;
            if (ps && ps.length > 0) {
              lines.push('{sep|──────────────}');
              ps.forEach(p => { lines.push(`{partner|${p.name}}`); });
            }
            return lines.join('\\n');
          },
          rich: {
            main: { fontWeight: 'bold', fontSize: 13, padding: [4,0,4,0] },
            gen: { fontSize: 11, color: '#3b82f6', fontWeight: 'bold' },
            sep: { color: '#ccc', height: 2 },
            partner: { fontSize: 11, color: '#666', padding: [2,0,2,0] }
          }"""

content = re.sub(r'formatter:\s*function\(params\)\s*\{.*?\},\s*rich:\s*\{.*?\}', new_formatter, content, flags=re.DOTALL)


# 4. Update expandPathToName
new_expand = """function expandPathToName(node, searchName) {
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
  let hasTargetChild = false;

  if (node.children && node.children.length > 0) {
    node.children.forEach(c => {
      let isChildTarget = (c.name.toLowerCase().includes(searchName) || 
                          (c.partners && c.partners.some(p => p.name.toLowerCase().includes(searchName))));
      if (isChildTarget) {
          hasTargetChild = true;
      }
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
    if (hasTargetChild) {
        node.collapsed = false;
    } else {
        node.children = matchedChildren;
        if (node.partners) {
           let arr = Array.from(neededPartnerIds);
           node.partners = node.partners.filter(p => arr.includes(p.id));
        }
        node.collapsed = false;
    }
  } else if (isTarget) {
    node.collapsed = false; 
    node.itemStyle = { borderColor: '#ef4444', borderWidth: 3 };
    node.label = { backgroundColor: '#fee2e2', borderColor: '#ef4444' };
  } else {
    node.collapsed = true;
  }
  return found;
}"""

content = re.sub(r'function expandPathToName\(node, searchName\).*?return found;\s*}', new_expand, content, flags=re.DOTALL)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)

print("JS Updated successfully.")
