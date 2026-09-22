
import builtins
import os

original_open = builtins.open

def mocked_open(file, mode='r', *args, **kwargs):
    if 'w' in mode:
        if 'sahabat_etf.js' not in str(file):
            # Return a dummy file object that does nothing
            class DummyFile:
                def write(self, *a, **k): pass
                def __enter__(self): return self
                def __exit__(self, *a, **k): pass
            return DummyFile()
    return original_open(file, mode, *args, **kwargs)

builtins.open = mocked_open

try:
    file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    import re
    
    # Remove old select change listener
    target1 = r'const pohonYearSelect = document\.getElementById\("setf-pohon-year"\);\s*if \(pohonYearSelect\) \{\s*pohonYearSelect\.addEventListener\("change", function \(\) \{\s*if \(window\._setfPohonLoaded\) setfLoadPohon\(\);\s*\}\);\s*\}'
    content = re.sub(target1, '', content)
    
    # Modify setfLoadPohon
    target2 = r'function setfLoadPohon\(\) \{\s*const selYear = document\.getElementById\(\'setf-pohon-year\'\);\s*const selMonth = document\.getElementById\(\'setf-pohon-month\'\);\s*if \(!selYear\) return;\s*const pillars = Array\.from\(document\.querySelectorAll\(\'\.setf-pohon-pillar-cb:checked\'\)\)\.map\(cb => cb\.value\);\s*let qs = \'year=\' \+ encodeURIComponent\(selYear\.value\);'
    
    replacement2 = """function setfLoadPohon() {
      const years = Array.from(document.querySelectorAll('.setf-pohon-year-cb:checked')).map(cb => cb.value);
      const selMonth = document.getElementById('setf-pohon-month');
      
      const pillars = Array.from(document.querySelectorAll('.setf-pohon-pillar-cb:checked')).map(cb => cb.value);
      
      let qs = '';
      years.forEach(y => { qs += 'years[]=' + encodeURIComponent(y) + '&'; });
      qs = qs.slice(0, -1);
    """
    
    content = re.sub(target2, replacement2, content)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated js")
    
except Exception as e:
    print("Error:", e)
