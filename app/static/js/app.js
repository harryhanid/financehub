async function apiFetch(url, options = {}) {
  const defaults = {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  };
  const resp = await fetch(url, { ...defaults, ...options });
  if (resp.status === 401) {
    const refreshed = await tryRefresh();
    if (refreshed) return fetch(url, { ...defaults, ...options });
    window.location.href = "/auth/login";
    return null;
  }
  return resp;
}

async function tryRefresh() {
  const resp = await fetch("/auth/refresh", {
    method: "POST", credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  return resp.ok;
}

function doLogout() {
  apiFetch("/auth/logout", { method: "POST", body: JSON.stringify({}) })
    .then(() => { window.location.href = "/auth/login"; });
}

function initTabs(container) {
  const tabs = container.querySelectorAll(".tab-btn");
  const panels = container.querySelectorAll(".tab-panel");
  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      panels.forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const target = container.querySelector(`#${btn.dataset.tab}`);
      if (target) target.classList.add("active");
    });
  });
  if (tabs.length > 0) tabs[0].click();
}

function fmtRupiah(n) {
  return new Intl.NumberFormat("id-ID").format(n || 0);
}

function showToast(msg, type = "success") {
  let toast = document.getElementById("fh-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "fh-toast";
    toast.style.cssText = "position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;padding:.75rem 1.25rem;border-radius:8px;font-size:.875rem;box-shadow:0 4px 12px rgba(0,0,0,.15);transition:opacity .3s;max-width:360px;";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.background = type === "success" ? "#065f46" : "#991b1b";
  toast.style.color = "#fff";
  toast.style.opacity = "1";
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { toast.style.opacity = "0"; }, 3000);
}

function openModal(id) { const el = document.getElementById(id); if (el) el.classList.add("open"); }
function closeModal(id) { const el = document.getElementById(id); if (el) el.classList.remove("open"); }

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", e => { if (e.target === overlay) overlay.classList.remove("open"); });
  });
});
