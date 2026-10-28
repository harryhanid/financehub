import re

with open('C:/Financehub/app/templates/beasiswa/approval.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the whole <script> block
new_script = '''<script>
function toggleDetail(batch_id) {
  const tr = document.getElementById('detail-' + batch_id);
  if(tr.classList.contains('open')) tr.classList.remove('open');
  else tr.classList.add('open');
}

function toggleAllCheck(el, batch_id) {
  const cbs = document.querySelectorAll('.cb-' + batch_id);
  cbs.forEach(cb => cb.checked = el.checked);
}

function getSelectedIds(batch_id) {
  const cbs = document.querySelectorAll('.cb-' + batch_id + ':checked');
  return Array.from(cbs).map(cb => parseInt(cb.value));
}

function getAllIds(batch_id) {
  const cbs = document.querySelectorAll('.cb-' + batch_id);
  return Array.from(cbs).map(cb => parseInt(cb.value));
}

async function approveReq(ids) {
  if(!ids.length) { showToast("Tidak ada item yang dipilih", "error"); return; }
  if(!confirm("Yakin ingin menyetujui " + ids.length + " pengajuan ini?")) return;
  const res = await apiFetch("/beasiswa/approval-budget/approve", {
    method: "POST", body: JSON.stringify({request_ids: ids})
  });
  const d = await res.json();
  showToast(d.pesan, d.ok ? "success" : "error");
  if(d.ok) setTimeout(() => location.reload(), 800);
}

async function rejectReq(ids) {
  if(!ids.length) { showToast("Tidak ada item yang dipilih", "error"); return; }
  const reason = prompt("Masukkan alasan penolakan:");
  if(reason === null) return;
  if(reason.trim() === "") { showToast("Alasan wajib diisi", "error"); return; }
  
  const res = await apiFetch("/beasiswa/approval-budget/reject", {
    method: "POST", body: JSON.stringify({request_ids: ids, reason: reason.trim()})
  });
  const d = await res.json();
  showToast(d.pesan, d.ok ? "success" : "error");
  if(d.ok) setTimeout(() => location.reload(), 800);
}

function approveBatch(batch_id) { approveReq(getAllIds(batch_id)); }
function rejectBatch(batch_id) { rejectReq(getAllIds(batch_id)); }
function approveSelected(batch_id) { approveReq(getSelectedIds(batch_id)); }
function rejectSelected(batch_id) { rejectReq(getSelectedIds(batch_id)); }
</script>'''

content = re.sub(r'(?sm)<script>.*?</script>', new_script, content)

with open('C:/Financehub/app/templates/beasiswa/approval.html', 'w', encoding='utf-8') as f:
    f.write(content)
