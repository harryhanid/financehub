import sys

with open('pristine_sahabat.js', 'r', encoding='utf-8') as f:
    p_content = f.read()

start_str = "function setfApplyFilters() {"
end_str = '.catch(function () { showToast("Gagal memuat detail transaksi.", "error"); });\n}'

start_idx = p_content.find(start_str)
end_idx = p_content.find(end_str) + len(end_str)

missing_code = p_content[start_idx:end_idx]

with open('app/static/js/sahabat_etf.js', 'r', encoding='utf-8') as f:
    target_content = f.read()

target_start = target_content.find('function setfApplyFilters() {')
target_end = target_content.find('// --- Diagram Pohon ---')

if target_start != -1 and target_end != -1:
    new_content = target_content[:target_start] + missing_code + '\n\n' + target_content[target_end:]
    with open('app/static/js/sahabat_etf.js', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Successfully patched sahabat_etf.js again')
else:
    print('Could not find boundaries in target')
