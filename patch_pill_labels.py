import sys

def patch():
    with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'r', encoding='utf-8') as f:
        content = f.read()

    old_color_logic = """          color: function(context) {
             const bg = context.dataset.backgroundColor;
             return setfGetContrastYIQ(bg) === 'dark' ? '#0f172a' : '#ffffff';
          },"""

    new_color_logic = """          color: '#ffffff',
          backgroundColor: 'rgba(0, 0, 0, 0.35)',
          borderRadius: 4,
          padding: { top: 2, bottom: 2, left: 4, right: 4 },"""

    if old_color_logic in content:
        content = content.replace(old_color_logic, new_color_logic)
        with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched datalabels successfully.")
    else:
        print("Could not find color logic")

if __name__ == '__main__':
    patch()
