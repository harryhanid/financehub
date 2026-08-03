path = r"C:\Financehub\app\static\css\budget.css"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

new_css = """
.budget-table-container {
  max-height: calc(100vh - 220px);
  overflow-y: auto;
  border-radius: var(--radius-md);
  box-shadow: 0 0 0 1px var(--border-color); /* fake border */
}

.budget-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--bg-card);
  border-radius: var(--radius-md);
}

.budget-table th {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg-card);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  padding: 0.6rem 0.9rem;
  border-bottom: 1px solid var(--border-color);
  text-align: left;
}
"""

c = c.replace(
""".budget-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  overflow: hidden;
}""",
""".budget-table-container {
  max-height: calc(100vh - 220px);
  overflow-y: auto;
  border-radius: var(--radius-md);
  box-shadow: 0 0 0 1px var(--border-color);
}
.budget-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--bg-card);
  border-radius: var(--radius-md);
}"""
)

import re
c = re.sub(
r'\.budget-table th \{.*?(?=\n\.budget-table tr)',
r'.budget-table th {\n  position: sticky;\n  top: 0;\n  z-index: 10;\n  background: var(--bg-card);\n  backdrop-filter: blur(12px);\n  -webkit-backdrop-filter: blur(12px);\n  color: var(--text-secondary);\n  font-weight: 600;\n  text-transform: uppercase;\n  font-size: 0.72rem;\n  letter-spacing: 0.04em;\n}',
c, flags=re.DOTALL
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done budget.css")
