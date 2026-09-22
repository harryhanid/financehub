import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

start = content.find("function setfRenderKategoriTable")
print(content[start+1500:start+3500])
