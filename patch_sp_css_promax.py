import sys
import re

def patch_css():
    with open(r'C:\Financehub\sponsorship_clean.css', 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace the existing .sp-form-card
    old_card = """.sp-form-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1.25rem 1.5rem;
}"""
    
    new_card = """.sp-form-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.5rem 2rem;
  box-shadow: 0 4px 20px -4px rgba(0,0,0,0.05);
  transition: box-shadow 0.3s ease;
}
[data-theme="dark"] .sp-form-card {
  box-shadow: 0 4px 20px -4px rgba(0,0,0,0.2);
  border-color: rgba(255,255,255,0.08);
  background: linear-gradient(145deg, var(--bg-card), rgba(255,255,255,0.02));
}"""

    content = content.replace(old_card, new_card)
    
    # Append Promax CSS
    promax_css = """
/* --- UI/UX Promax Enhancements for Input Form --- */

.sp-form-field input,
.sp-form-field select {
  transition: all 0.2s ease;
}
.sp-form-field input:focus,
.sp-form-field select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}
[data-theme="dark"] .sp-form-field input:focus,
[data-theme="dark"] .sp-form-field select:focus {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
}

.sp-promax-line-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  padding: 1.25rem 1.5rem 0.5rem 1.5rem;
  border-radius: 10px;
  margin-bottom: 1.25rem;
  box-shadow: 0 2px 10px -2px rgba(0,0,0,0.03);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.sp-promax-line-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px -4px rgba(0,0,0,0.08);
  border-color: var(--sl-300);
}
[data-theme="dark"] .sp-promax-line-card {
  background: rgba(255,255,255,0.015);
  border-color: rgba(255,255,255,0.06);
}
[data-theme="dark"] .sp-promax-line-card:hover {
  border-color: rgba(255,255,255,0.15);
  box-shadow: 0 8px 24px -4px rgba(0,0,0,0.3);
}

.sp-promax-remove-btn {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0.35rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}
.sp-promax-remove-btn:hover {
  background: #fef2f2;
  color: #ef4444;
}
[data-theme="dark"] .sp-promax-remove-btn:hover {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.sp-promax-add-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: transparent;
  border: 1.5px dashed var(--sl-300);
  color: var(--text-muted);
  padding: 0.75rem 1.25rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
  justify-content: center;
}
.sp-promax-add-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: rgba(59, 130, 246, 0.05);
}
[data-theme="dark"] .sp-promax-add-btn {
  border-color: rgba(255,255,255,0.15);
}
[data-theme="dark"] .sp-promax-add-btn:hover {
  background: rgba(59, 130, 246, 0.1);
  border-color: var(--primary);
}

.sp-promax-footer {
  margin-top: 2rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
}
.sp-promax-submit-btn {
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: #fff;
  border: none;
  padding: 0.75rem 2.5rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  transition: all 0.2s ease;
}
.sp-promax-submit-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
}
.sp-promax-submit-btn:active {
  transform: translateY(1px);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}
"""
    content += promax_css

    with open(r'C:\Financehub\app\static\css\sponsorship.css', 'w', encoding='utf-8') as f:
        f.write(content)

    print("Patched sponsorship.css successfully!")

if __name__ == '__main__':
    patch_css()
