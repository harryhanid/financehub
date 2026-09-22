import sys

def patch_file(filepath, func_name, formatter_func):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # The current code has the dynamic colors
    # We will search for the dynamic colors and replace them with static colors
    
    old_colors = f"""  const budgetColors = labels.map(l => l === "Total" ? (isDark ? "#475569" : "#94a3b8") : dashColorForCategory(l) + "66");
  const realisasiColors = labels.map(l => l === "Total" ? (isDark ? "#3b82f6" : "#2563eb") : dashColorForCategory(l));"""
    
    if 'sahabat' in filepath:
        old_colors = f"""  const budgetColors = labels.map(l => l === "Total" ? (isDark ? "#475569" : "#94a3b8") : setfColorForCategory(l) + "66");
  const realisasiColors = labels.map(l => l === "Total" ? (isDark ? "#3b82f6" : "#2563eb") : setfColorForCategory(l));"""

    new_colors = """  const budgetColor = "rgba(148, 163, 184, 0.8)"; // Slate 400
  const realisasiColor = "rgba(59, 130, 246, 0.9)"; // Blue 500"""

    if old_colors in content:
        content = content.replace(old_colors, new_colors)
        
        # Now fix the dataset backgrounds
        content = content.replace("backgroundColor: budgetColors,", "backgroundColor: budgetColor,")
        content = content.replace("backgroundColor: realisasiColors,", "backgroundColor: realisasiColor,")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {filepath} successfully!")
    else:
        print(f"Could not find old colors in {filepath}")

if __name__ == '__main__':
    patch_file(r'C:\Financehub\app\static\js\sahabat_etf.js', 'setfRenderBudgetVsRealisasiChart', 'setfFmtJutaan')
    patch_file(r'C:\Financehub\app\static\js\dashboard_beasiswa.js', 'dashRenderBudgetVsRealisasiChart', 'dashFmtJutaan')
