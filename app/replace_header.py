import re

with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "r", encoding="utf-8") as f:
    content = f.read()

old_header_block = """<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
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

new_header_block = """<div style="display: flex; align-items: center; margin-bottom: 24px; gap: 14px;">
        <div style="display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1.25rem; color: #1e293b; letter-spacing: -0.02em;">
            <span style="display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; background: var(--sl-50); border: 1px solid var(--sl-200); border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,.02);">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
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
        <div style="color: #cbd5e1; font-size: 1.5rem; font-weight: 300; padding-bottom: 2px;">|</div>
        <h2 style="margin: 0; color: #1e293b; font-size: 1.25rem; font-weight: 600;">Sahabat ETF</h2>
    </div>"""

if old_header_block in content:
    content = content.replace(old_header_block, new_header_block)
    with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated header block!")
else:
    print("Could not find old header block string!")
