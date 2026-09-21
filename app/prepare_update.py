import re

with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Restore initTreeQuery to wrap json.data in Sahabat ETF
init_old = """    treeRawData = json.data;
    treeRawData.forEach(r => assignGenerations(r, 0));"""
init_new = """    treeRawData = {
      name: "Sahabat ETF",
      children: json.data
    };
    assignGenerations(treeRawData, 0);"""
content = content.replace(init_old, init_new)

# 2. Restore assignGenerations to handle single node and depth
gen_old = """function assignGenerations(node, depth) {
  node.genLabel = "Gen " + (depth + 1);
  if (node.children) {
    node.children.forEach(c => assignGenerations(c, depth + 1));
  }
}"""
gen_new = """function assignGenerations(node, depth) {
  if (depth > 0) {
    node.genLabel = "Gen " + depth;
  } else {
    node.genLabel = "";
  }
  if (node.children) {
    node.children.forEach(c => assignGenerations(c, depth + 1));
  }
}"""
content = content.replace(gen_old, gen_new)

# 3. Restore collectNames
dl_old = """treeRawData.forEach(c => collectNames(c));"""
dl_new = """if (treeRawData.children) treeRawData.children.forEach(c => collectNames(c));"""
content = content.replace(dl_old, dl_new)

# 4. Update renderTree to accept array
render_old = """data: data,"""
render_new = """data: dataArray,"""
content = content.replace(render_old, render_new)
content = content.replace("function renderTree(data)", "function renderTree(dataArray)")
content = content.replace("expandPathToName(dataCopy, q);\n  // force update\n  renderTree(dataCopy);", "expandPathToName(dataCopy, q);\n  // force update\n  renderTree([dataCopy]);")
content = content.replace("renderTree(treeRawData);", "renderTree([treeRawData]);")

# 5. Update searchTree to bypass Sahabat ETF if only 1 child matches
search_old = """function searchTree() {
  const q = document.getElementById("tree-search-input").value.toLowerCase();
  if (!q) {
    renderTree([treeRawData]);
    return;
  }
  let dataCopy = JSON.parse(JSON.stringify(treeRawData));
  dataCopy.forEach(root => expandPathToName(root, q));
  // force update
  renderTree([dataCopy]);
}"""
# Wait, search_old is what is currently in the file? Let's check what's actually there.
