import subprocess
out = subprocess.check_output(['git', 'show', 'HEAD:app/static/js/sahabat_etf.js'], cwd='C:/Financehub').decode('utf-8')
print('Does setfApplyFilters exist in HEAD?:', 'function setfApplyFilters() {' in out)
start = out.find('fetch("/beasiswa/sahabat/api/breakdown"')
if start != -1:
    end = out.find('.catch(', start)
    print(out[start:end+50])
else:
    print('Not found')
