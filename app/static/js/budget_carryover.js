// static/js/budget_carryover.js

// Budget picker: debounced search fills the <datalist>; picking an id shows
// what that budget is so nobody files a request against the wrong one.
let _crSearchTimer, _crHits = {};
function crBudgetSearch(q) {
  _crShowInfo(q);
  clearTimeout(_crSearchTimer);
  if (q.trim().length < 2) return;
  _crSearchTimer = setTimeout(async () => {
    const resp = await apiFetch("/budget/api/search?" + new URLSearchParams({ q: q.trim() }));
    if (!resp) return;
    const rows = (await resp.json()).rows || [];
    const list = document.getElementById("cr-budget-options");
    list.innerHTML = "";
    rows.forEach(r => {
      _crHits[r.id] = r;
      const o = document.createElement("option");
      o.value = r.id;
      o.label = `${r.description || r.gl_description || "-"} · ${r.dept || ""} · ${fmtRupiah(r.amount)}`;
      list.appendChild(o);
    });
    _crShowInfo(document.getElementById("cr-budget-id").value);
  }, 250);
}
function _crShowInfo(id) {
  const info = document.getElementById("cr-budget-info");
  const r = _crHits[id.trim()];
  info.textContent = r
    ? `${r.description || r.gl_description || "-"} · ${r.dept || "-"} · Rp ${fmtRupiah(r.amount)} · deadline ${r.deadline || "-"}`
    : "Ketik minimal 2 huruf lalu pilih budget dari daftar.";
  info.classList.toggle("cr-help-ok", !!r);
}
function _crValidate(needAmount) {
  const idEl = document.getElementById("cr-budget-id"), reasonEl = document.getElementById("cr-reason");
  if (!idEl.value.trim()) { showToast("Pilih budget terlebih dahulu.", "warning"); idEl.focus(); return false; }
  if (!reasonEl.value.trim()) { showToast("Alasan wajib diisi.", "warning"); reasonEl.focus(); return false; }
  const amtEl = document.getElementById("cr-amount");
  if (needAmount && !(parseFloat(amtEl.value) > 0)) { showToast("Isi jumlah tambahan lebih dari 0.", "warning"); amtEl.focus(); return false; }
  return true;
}

async function budgetSubmitCarryover() {
  if (!_crValidate(false)) return;
  const budgetId = document.getElementById("cr-budget-id").value.trim();
  const reason = document.getElementById("cr-reason").value;
  showLoading("Mengirim request carryover...");
  try {
    const resp = await apiFetch("/budget/carryover/request", {
      method: "POST", body: JSON.stringify({ budget_id: budgetId, reason: reason }),
    });
    const data = await resp.json();
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) setTimeout(() => window.location.reload(), 1000);
  } catch (e) {
    showToast("Gagal mengirim request carryover.", "error");
  } finally {
    hideLoading();
  }
}

async function budgetSubmitAdditional() {
  if (!_crValidate(true)) return;
  const budgetId = document.getElementById("cr-budget-id").value.trim();
  const reason = document.getElementById("cr-reason").value;
  const amount = document.getElementById("cr-amount").value;
  showLoading("Mengirim request tambahan anggaran...");
  try {
    const resp = await apiFetch("/budget/additional/request", {
      method: "POST", body: JSON.stringify({ budget_id: budgetId, amount: amount, reason: reason }),
    });
    const data = await resp.json();
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) setTimeout(() => window.location.reload(), 1000);
  } catch (e) {
    showToast("Gagal mengirim request tambahan anggaran.", "error");
  } finally {
    hideLoading();
  }
}

async function budgetApproveRequest(budgetId, type) {
  const months = await promptModal("", {
    title: "Setujui " + type, label: "Perpanjangan (bulan)", inputType: "number", required: true,
    defaultValue: type === "Carryover" ? "12" : "3", confirmText: "Setujui",
    validate: v => (parseInt(v, 10) > 0 ? "" : "Isi jumlah bulan lebih dari 0."),
  });
  if (months === null) return;
  const endpoint = type === "Carryover" ? "/budget/carryover/" : "/budget/additional/";
  showLoading("Memproses approval...");
  try {
    const resp = await apiFetch(endpoint + budgetId + "/approve", {
      method: "POST", body: JSON.stringify({ extension_months: months }),
    });
    const data = await resp.json();
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) setTimeout(() => window.location.reload(), 1000);
  } catch (e) {
    showToast("Gagal memproses approval.", "error");
  } finally {
    hideLoading();
  }
}

async function budgetRejectRequest(budgetId, type) {
  const reason = await promptModal("", {
    title: "Tolak " + type, label: "Alasan penolakan", multiline: true,
    type: "danger", confirmText: "Tolak",
  });
  if (reason === null) return;
  const endpoint = type === "Carryover" ? "/budget/carryover/" : "/budget/additional/";
  showLoading("Menolak request...");
  try {
    const resp = await apiFetch(endpoint + budgetId + "/reject", {
      method: "POST", body: JSON.stringify({ reason: reason }),
    });
    const data = await resp.json();
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) setTimeout(() => window.location.reload(), 1000);
  } catch (e) {
    showToast("Gagal menolak request.", "error");
  } finally {
    hideLoading();
  }
}
