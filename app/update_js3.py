import re

with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update initTreeQuery
init_old = """    treeRawData = {
      name: "Sahabat ETF",
      children: json.data
    };
    assignGenerations(treeRawData, 0);"""
init_new = """    treeRawData = json.data;
    treeRawData.forEach(r => assignGenerations(r, 0));"""
content = content.replace(init_old, init_new)

# 2. Update assignGenerations
gen_old = """function assignGenerations(node, depth) {
  if (depth > 0) {
    node.genLabel = "Gen " + depth;
  } else {
    node.genLabel = "";
  }
  if (node.children) {
    node.children.forEach(c => assignGenerations(c, depth + 1));
  }
}"""
gen_new = """function assignGenerations(node, depth) {
  node.genLabel = "Gen " + (depth + 1);
  if (node.children) {
    node.children.forEach(c => assignGenerations(c, depth + 1));
  }
}"""
content = content.replace(gen_old, gen_new)

# 3. Update datalist populator
dl_old = """treeRawData.children.forEach(c => collectNames(c));"""
dl_new = """treeRawData.forEach(c => collectNames(c));"""
content = content.replace(dl_old, dl_new)

# 4. Update renderTree to accept array directly
render_old = """data: [data],"""
render_new = """data: data,"""
content = content.replace(render_old, render_new)

# 5. Update searchTree
search_old = """  let dataCopy = JSON.parse(JSON.stringify(treeRawData));
  expandPathToName(dataCopy, q);"""
search_new = """  let dataCopy = JSON.parse(JSON.stringify(treeRawData));
  dataCopy.forEach(root => expandPathToName(root, q));"""
content = content.replace(search_old, search_new)

# 6. Update formatter to append IDs
formatter_old = """          formatter: function(params) {
            let n = params.data.name;
            let gen = params.data.genLabel ? `{gen|[${params.data.genLabel}]} ` : '';
            let lines = [`${gen}{main|${n}}`];
            let ps = params.data.partners;
            if (ps && ps.length > 0) {
              lines.push('{sep|---------------}');
              ps.forEach(p => { lines.push(`{partner|${p.name}}`); });
            }
            return lines.join('\\n');
          },"""

formatter_new = """          formatter: function(params) {
            let n = params.data.name;
            let lastCode = params.data.id ? params.data.id.split('.').pop() : '';
            if (lastCode && lastCode !== 'A' && lastCode !== 'B') {
                n = n + ' (' + lastCode + ')';
            }
            let gen = params.data.genLabel ? `{gen|[${params.data.genLabel}]} ` : '';
            let lines = [`${gen}{main|${n}}`];
            let ps = params.data.partners;
            if (ps && ps.length > 0) {
              lines.push('{sep|---------------}');
              ps.forEach(p => {
                  let pCode = p.id ? p.id.split('.').pop() : '';
                  let pName = p.name;
                  if (pCode && pCode !== 'A' && pCode !== 'B') {
                      pName = pName + ' (' + pCode + ')';
                  }
                  lines.push(`{partner|${pName}}`); 
              });
            }
            return lines.join('\\n');
          },"""
content = re.sub(r'formatter:\s*function\(params\)\s*\{.*?return lines\.join\(\'\\n\'\);\s*\},', formatter_new, content, flags=re.DOTALL)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated JS without fake root and with appended codes.")
