file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """const SETF_PILLAR_BADGE_CLASS = {
  "AGRI": "badge-pil-agri",
  "APP": "badge-pil-app",
  "FINANCE": "badge-pil-finance",
};"""

repl = """const SETF_PILLAR_BADGE_CLASS = {
  "AGRI": "badge-pil-agri",
  "APP": "badge-pil-app",
  "FINANCE": "badge-pil-finance",
  "SETF": "badge-pil-setf",
};"""

content = content.replace(target, repl)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Added SETF back!")
