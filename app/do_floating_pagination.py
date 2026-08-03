# 1. Update style.css
css_path = r"C:\Financehub\app\static\css\style.css"
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

floating_css = """
/* Floating Glassmorphic Pagination */
.floating-pagination {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 16px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 10px 24px;
  border-radius: 9999px;
  box-shadow: 0 10px 40px -10px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.4) inset;
  z-index: 100;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 0.8rem;
}
.floating-pagination:hover {
  box-shadow: 0 15px 50px -10px rgba(0,0,0,0.25), 0 0 0 1px rgba(255,255,255,0.5) inset;
  transform: translateX(-50%) translateY(-2px);
}
[data-theme="dark"] .floating-pagination {
  background: rgba(30, 33, 43, 0.75);
  box-shadow: 0 10px 40px -10px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05) inset;
  color: #e2e8f0;
}
[data-theme="dark"] .floating-pagination:hover {
  box-shadow: 0 15px 50px -10px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.1) inset;
}
.floating-pagination .btn {
  border-radius: 9999px;
  padding: 6px 16px;
  font-weight: 500;
  border: none;
  background: rgba(0, 0, 0, 0.05);
  color: var(--text-main);
  transition: background 0.2s, color 0.2s;
  cursor: pointer;
  text-decoration: none;
}
[data-theme="dark"] .floating-pagination .btn {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}
.floating-pagination .btn:hover:not([style*="pointer-events:none"]):not(:disabled) {
  background: var(--primary, #3b82f6);
  color: #fff;
}
.floating-pagination .btn:disabled,
.floating-pagination .btn[style*="pointer-events:none"] {
  opacity: 0.5;
  cursor: not-allowed;
}
"""
if ".floating-pagination" not in css:
    css += "\n" + floating_css
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css)


# 2. Update etf_payment_application/index.html
etf_path = r"C:\Financehub\app\templates\etf_payment_application\index.html"
with open(etf_path, "r", encoding="utf-8") as f:
    etf_html = f.read()

# Replace main pagination div
etf_html = etf_html.replace(
    '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:8px;padding:6px 2px;font-size:.8rem">',
    '<div class="floating-pagination">'
)
# Replace summary pagination div
etf_html = etf_html.replace(
    '<div id="summary-pagination" style="display:none;align-items:center;justify-content:space-between;gap:8px;margin-top:8px;padding:6px 2px;font-size:.8rem">',
    '<div id="summary-pagination" class="floating-pagination" style="display:none;">'
)
# Remove the old mainPadBottom logic that subtracted 28px, making it subtract 0px (so table takes full height)
etf_html = etf_html.replace(
    'const mainPadBottom = 28;',
    'const mainPadBottom = 0;'
)

with open(etf_path, "w", encoding="utf-8") as f:
    f.write(etf_html)


# 3. Update payment_memo/index.html
memo_path = r"C:\Financehub\app\templates\payment_memo\index.html"
with open(memo_path, "r", encoding="utf-8") as f:
    memo_html = f.read()

# Replace pam-pagination and smt-pagination
memo_html = memo_html.replace(
    '<div id="pam-pagination" style="display:none;align-items:center;justify-content:space-between;gap:8px;margin-top:8px;padding:6px 2px;font-size:12px">',
    '<div id="pam-pagination" class="floating-pagination" style="display:none;">'
)
memo_html = memo_html.replace(
    '<div id="smt-pagination" style="display:none;align-items:center;justify-content:space-between;gap:8px;margin-top:8px;padding:6px 2px;font-size:12px">',
    '<div id="smt-pagination" class="floating-pagination" style="display:none;">'
)
memo_html = memo_html.replace(
    'const mainPadBottom = 28;',
    'const mainPadBottom = 0;'
)

with open(memo_path, "w", encoding="utf-8") as f:
    f.write(memo_html)

# 4. Update sponsorship/data.html
spon_path = r"C:\Financehub\app\templates\sponsorship\data.html"
with open(spon_path, "r", encoding="utf-8") as f:
    spon_html = f.read()

import re
# Replace budget-pagination
spon_html = re.sub(
    r'<div class="budget-pagination"[^>]*>', 
    '<div class="floating-pagination">', 
    spon_html
)

with open(spon_path, "w", encoding="utf-8") as f:
    f.write(spon_html)

print("Update complete")
