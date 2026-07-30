import re
import sys

def replace_in_file(path, old, new):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if old in content:
        content = content.replace(old, new)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {path}")
    else:
        print(f"Target not found in {path}")

# For payment_memo
pm_path = r'C:\Financehub\app\templates\payment_memo\index.html'
pm_old = """function sizePillarWraps() {
  requestAnimationFrame(() => {
    const mainPadBottom = 28; // .main { padding: 1.75rem } \u2014 1.75\u00d716 = 28px
    document.querySelectorAll('.pillar-table-wrap').forEach(wrap => {
      if (!wrap.offsetParent) return;
      wrap.style.height = (window.innerHeight - wrap.getBoundingClientRect().top - mainPadBottom) + 'px';
    });
  });
}"""
pm_old2 = """function sizePillarWraps() {
  requestAnimationFrame(() => {
    const mainPadBottom = 28; // .main { padding: 1.75rem } \u2014 1.75\u00d716 = 28px
    document.querySelectorAll('.pillar-table-wrap').forEach(wrap => {
      if (!wrap.offsetParent) return;
      let pagHeight = 0;
      const pagEl = wrap.nextElementSibling;
      if (pagEl && pagEl.innerText && pagEl.innerText.includes('Menampilkan')) pagHeight = 40;
      wrap.style.height = (window.innerHeight - wrap.getBoundingClientRect().top - mainPadBottom - pagHeight) + 'px';
    });
  });
}"""

pm_new = """function sizePillarWraps() {
  requestAnimationFrame(() => {
    const mainPadBottom = 28; // .main { padding: 1.75rem } 
    document.querySelectorAll('.pillar-table-wrap').forEach(wrap => {
      if (!wrap.offsetParent) return;
      let pagHeight = 0;
      const pagEl = wrap.nextElementSibling;
      if (pagEl && pagEl.innerText && pagEl.innerText.includes('Menampilkan')) pagHeight = 44;
      wrap.style.height = (window.innerHeight - wrap.getBoundingClientRect().top - mainPadBottom - pagHeight) + 'px';
    });
  });
}"""

# I will use regex to handle the weird characters like em dash
pm_pattern = r'function sizePillarWraps\(\) \{\s*requestAnimationFrame\(\(\) => \{\s*const mainPadBottom = 28;.*?\n\s*document\.querySelectorAll\(\'\.pillar-table-wrap\'\)\.forEach\(wrap => \{\s*if \(\!wrap\.offsetParent\) return;\s*wrap\.style\.height = \(window\.innerHeight - wrap\.getBoundingClientRect\(\)\.top - mainPadBottom\) \+ \'px\';\s*\}\);\s*\}\);\s*\}'
pm_repl = """function sizePillarWraps() {
  requestAnimationFrame(() => {
    const mainPadBottom = 28;
    document.querySelectorAll('.pillar-table-wrap').forEach(wrap => {
      if (!wrap.offsetParent) return;
      let pagHeight = 0;
      const pagEl = wrap.nextElementSibling;
      if (pagEl && pagEl.innerText && pagEl.innerText.includes('Menampilkan')) pagHeight = 44;
      wrap.style.height = (window.innerHeight - wrap.getBoundingClientRect().top - mainPadBottom - pagHeight) + 'px';
    });
  });
}"""

with open(pm_path, 'r', encoding='utf-8') as f:
    c = f.read()
c, count = re.subn(pm_pattern, pm_repl, c, flags=re.DOTALL)
if count > 0:
    with open(pm_path, 'w', encoding='utf-8') as f:
        f.write(c)
    print(f"Updated {pm_path}")
else:
    print(f"Not found in {pm_path}")
