file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

badge_code = """const SETF_PILLAR_BADGE_CLASS = {
  "AGRI": "badge-pil-agri",
  "APP": "badge-pil-app",
  "FINANCE": "badge-pil-finance",
  "SETF": "badge-pil-setf",
};
function setfPillarBadge(pillar) {
  if (!pillar) return "";
  const cls = SETF_PILLAR_BADGE_CLASS[pillar.toUpperCase()] || "badge-cat-lainnya";
  return '<span class="budget-badge ' + cls + '">' + pillar + '</span>';
}
"""

content = content.replace(badge_code, "", 1) # replace first occurrence

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Removed duplicate!")
