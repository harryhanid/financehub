import re

with open('C:/Financehub/app/static/css/beasiswa_dashboard.css', 'r', encoding='utf-8') as f:
    content = f.read()

new_label_css = '''.beasiswa-dash-filter-panel .panel-opts label {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  text-align: left !important;
  gap: 0.5rem !important;
  font-size: 0.78rem;
  color: var(--text);
  font-weight: 500;
  white-space: nowrap;
  width: 100% !important;
  padding: 4px 0;
  line-height: 1.2;
}
.beasiswa-dash-filter-panel .panel-opts label input[type="checkbox"] {
  margin: 0 !important;
  flex: 0 0 auto !important;
}
.beasiswa-dash-filter-panel .panel-opts label span.filter-text {
  flex: 1 1 auto !important;
  text-align: left !important;
  white-space: normal !important;
}'''

content = re.sub(r'\.beasiswa-dash-filter-panel \.panel-opts label \{.*?\n\}', new_label_css, content, flags=re.DOTALL)

with open('C:/Financehub/app/static/css/beasiswa_dashboard.css', 'w', encoding='utf-8') as f:
    f.write(content)
