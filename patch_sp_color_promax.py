import sys

def add_colors():
    with open(r'C:\Financehub\app\static\css\sponsorship.css', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Enhance the card
    old_card = """.sp-form-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.5rem 2rem;
  box-shadow: 0 4px 20px -4px rgba(0,0,0,0.05);
  transition: box-shadow 0.3s ease;
}"""
    new_card = """.sp-form-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-top: 4px solid transparent;
  background-clip: padding-box;
  position: relative;
  border-radius: 12px;
  padding: 1.75rem 2.25rem;
  box-shadow: 0 8px 30px -4px rgba(0,0,0,0.08);
  transition: box-shadow 0.3s ease;
}
.sp-form-card::before {
  content: "";
  position: absolute;
  top: -4px; left: -1px; right: -1px; height: 4px;
  background: linear-gradient(135deg, var(--primary, #1e3a8a), #3b82f6);
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
}"""
    content = content.replace(old_card, new_card)

    # 2. Enhance section titles
    old_title = """.sp-form-section-title {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-secondary);
  margin-bottom: 0.75rem;
}"""
    new_title = """.sp-form-section-title {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--primary, #1d4ed8);
  margin-bottom: 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.sp-form-section-title::before {
  content: "";
  display: block;
  width: 12px;
  height: 12px;
  background: linear-gradient(135deg, var(--primary, #1e3a8a), #60a5fa);
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(59, 130, 246, 0.4);
}
[data-theme="dark"] .sp-form-section-title {
  color: #60a5fa;
}"""
    content = content.replace(old_title, new_title)

    # 3. Add accent to line cards
    old_line_card = """.sp-promax-line-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  padding: 1.25rem 1.5rem 0.5rem 1.5rem;
  border-radius: 10px;
  margin-bottom: 1.25rem;
  box-shadow: 0 2px 10px -2px rgba(0,0,0,0.03);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}"""
    new_line_card = """.sp-promax-line-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--sl-300, #cbd5e1);
  padding: 1.25rem 1.5rem 0.5rem 1.5rem;
  border-radius: 10px;
  margin-bottom: 1.25rem;
  box-shadow: 0 2px 10px -2px rgba(0,0,0,0.03);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease, border-color 0.2s ease;
}
.sp-promax-line-card:hover {
  border-left-color: #3b82f6;
}
[data-theme="dark"] .sp-promax-line-card {
  border-left-color: rgba(255,255,255,0.15);
}
[data-theme="dark"] .sp-promax-line-card:hover {
  border-left-color: #3b82f6;
}"""
    content = content.replace(old_line_card, new_line_card)

    with open(r'C:\Financehub\app\static\css\sponsorship.css', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    add_colors()
