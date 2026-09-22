file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """  });
},
      plugins: {"""
repl = """        },
      plugins: {"""

content = content.replace(target, repl)
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed syntax error!")
