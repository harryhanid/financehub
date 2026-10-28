import re

with open('C:/Financehub/app/static/css/beasiswa_dashboard.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the label block
new_label_css = '''.beasiswa-dash-filter-panel .panel-opts label {
  display: flex;
  align-items: center;
  justify-content: flex-start !important;
  text-align: left !important;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: var(--text);
  font-weight: 500;
  white-space: nowrap;
}
.beasiswa-dash-filter-panel .panel-opts label input {
  margin: 0 !important;
  flex-shrink: 0;
  margin-right: 0.4rem !important;
}'''

content = re.sub(r'\.beasiswa-dash-filter-panel \.panel-opts label \{.*?\n\}', new_label_css, content, flags=re.DOTALL)

with open('C:/Financehub/app/static/css/beasiswa_dashboard.css', 'w', encoding='utf-8') as f:
    f.write(content)
