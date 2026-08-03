path = r"C:\Financehub\app\static\css\sponsorship.css"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

new_css = """
/* Dashboard Scorecards */
.sp-scorecards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.sp-scorecard {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 15px 20px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  justify-content: center;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

[data-theme="dark"] .sp-scorecard {
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}

.sp-scorecard:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
}

.sp-scorecard-title {
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.sp-scorecard-amount {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.sp-scorecard-pct {
  font-size: 0.85rem;
  font-weight: 600;
}

.sp-scorecard-indicator {
  position: absolute;
  top: 0;
  right: 0;
  width: 4px;
  height: 100%;
}
"""
if ".sp-scorecards-grid" not in c:
    c += "\n" + new_css

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done sponsorship.css")
