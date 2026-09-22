with open('app/templates/payment_memo/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

attachment_cell_func = """
function _attachmentCell(r) {
  if (!r.attachment_file_id) return '<td style="padding:6px 8px;text-align:center">-</td>';
  const ids = r.attachment_file_id.split(',').filter(id => id.trim());
  if (!ids.length) return '<td style="padding:6px 8px;text-align:center">-</td>';
  return `<td style="padding:6px 8px;text-align:center;white-space:nowrap">
    ${ids.map((id, idx) => `<a href="/etf-payment-application/attachment/${id}" target="_blank" style="color:#2563eb;text-decoration:underline;font-size:11px;margin-right:4px" onclick="event.stopPropagation()">View ${idx+1}</a>`).join('<br>')}
  </td>`;
}
"""

content = content.replace('function _aksiCell(r) {', attachment_cell_func + '\nfunction _aksiCell(r) {')

import re
content = content.replace('<th style="padding:8px 10px;text-align:left;">Aksi</th>', '<th style="padding:8px 10px;text-align:left;">Lampiran</th>\n            <th style="padding:8px 10px;text-align:left;">Aksi</th>')
content = content.replace('<td style="padding:6px 8px">${_aksiCell(r)}</td>', '${_attachmentCell(r)}\n      <td style="padding:6px 8px">${_aksiCell(r)}</td>')
content = re.sub(r'colspan="(\d+)"([^>]*>Belum ada data|[^>]*>Memuat data)', lambda m: f'colspan="{int(m.group(1))+1}"{m.group(2)}', content)

with open('app/templates/payment_memo/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
