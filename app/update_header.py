import re

with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "r", encoding="utf-8") as f:
    content = f.read()

old_header = '<h2 style="margin-top: 0; margin-bottom: 20px; color: #1e293b;">Sahabat ETF</h2>'
new_header = """<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h2 style="margin: 0; color: #1e293b;">Sahabat ETF</h2>
        <div class="navbar-brand" style="margin-bottom: 0;">
            <span class="navbar-brand-icon">
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                <defs>
                  <linearGradient id="flow-mark-grad" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse">
                    <stop offset="0" style="stop-color:var(--accent)"/>
                    <stop offset="1" style="stop-color:var(--accent-2)"/>
                  </linearGradient>
                </defs>
                <path d="M2 13c2-4 4-4 6 0s4 4 6 0s3-5 3-5" stroke="url(#flow-mark-grad)" stroke-width="1.6" stroke-linecap="round"/>
                <path d="M2 8c2-4 4-4 6 0s4 4 6 0" stroke="url(#flow-mark-grad)" stroke-width="1.1" stroke-linecap="round" opacity="0.45"/>
              </svg>
            </span>
            FLOW
        </div>
    </div>"""

if old_header in content:
    content = content.replace(old_header, new_header)
    with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("Added FLOW logo to header!")
else:
    print("Could not find old header string!")
