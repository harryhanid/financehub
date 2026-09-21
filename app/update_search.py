import re

with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Restore initTreeQuery
content = content.replace("""    treeRawData = json.data;
    treeRawData.forEach(r => assignGenerations(r, 0));""",
"""    treeRawData = {
      name: "Sahabat ETF",
      children: json.data
    };
    assignGenerations(treeRawData, 0);""")

# 2. Restore assignGenerations
content = content.replace("""function assignGenerations(node, depth) {
  node.genLabel = "Gen " + (depth + 1);
  if (node.children) {
    node.children.forEach(c => assignGenerations(c, depth + 1));
  }
}""",
"""function assignGenerations(node, depth) {
  if (depth > 0) {
    node.genLabel = "Gen " + depth;
  } else {
    node.genLabel = "";
  }
  if (node.children) {
    node.children.forEach(c => assignGenerations(c, depth + 1));
  }
}""")

# 3. Restore collectNames
content = content.replace("treeRawData.forEach(c => collectNames(c));", "if (treeRawData.children) treeRawData.children.forEach(c => collectNames(c));")

# 4. Fix searchTree
search_old = """function searchTree() {
  const q = document.getElementById("tree-search-input").value.toLowerCase();
  if (!q) {
    renderTree(treeRawData);
    return;
  }
  let dataCopy = JSON.parse(JSON.stringify(treeRawData));
  dataCopy.forEach(root => expandPathToName(root, q));
  // force update
  renderTree(dataCopy);
}"""

search_new = """function searchTree() {
  const q = document.getElementById("tree-search-input").value.toLowerCase();
  if (!q) {
    renderTree([treeRawData]);
    return;
  }
  let dataCopy = JSON.parse(JSON.stringify(treeRawData));
  expandPathToName(dataCopy, q);
  
  if (dataCopy.children && dataCopy.children.length === 1) {
      renderTree([dataCopy.children[0]]);
  } else {
      renderTree([dataCopy]);
  }
}"""
content = content.replace(search_old, search_new)

# 5. Fix renderTree signature and parameter
content = content.replace("function renderTree(dataArray) {", "function renderTree(data) {")
# we must ensure that `data:` uses the array passed to renderTree.
# wait, if renderTree takes `data`, it is already passed as `[treeRawData]` in searchTree!
# so renderTree(data) where data is an array is perfectly fine.
# wait, what did my previous script do? `data: data,`
# Let's just make sure renderTree has `data: data,`
# if it has `data: dataArray,`, I'll change it back to `data: data,`
content = content.replace("data: dataArray,", "data: data,")

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated search logic!")
