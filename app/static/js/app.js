/* ── Module registry ──────────────────────────────────── */
const FH_MODULES = [
  { name: "Dashboard",             url: "/dashboard",               active: true  },
  { name: "Beasiswa",              url: "/beasiswa",                active: true  },
  { name: "Payment Approval Memo", url: "/payment-memo",            active: true  },
  { name: "Payment Application",   url: "/etf-payment-application", active: true  },
  { name: "Budget",                url: "/budget/",                 active: true  },
  { name: "Users",                 url: "/users",                   active: true  },
  { name: "Bank",                  url: null,                       active: false },
  { name: "Account Payable",       url: null,                       active: false },
  { name: "Advance",               url: null,                       active: false },
  { name: "Petty Cash",            url: null,                       active: false },
  { name: "Sponsorship",           url: null,                       active: false },
];
const FH_RECENT_KEY = 'fh_recent_modules';

function _fhGetRecent() {
  try { return JSON.parse(localStorage.getItem(FH_RECENT_KEY) || '[]'); } catch (e) { return []; }
}
function _fhRecordVisit(url) {
  if (!url) return;
  var recent = _fhGetRecent().filter(function(u) { return u !== url; });
  recent.unshift(url);
  localStorage.setItem(FH_RECENT_KEY, JSON.stringify(recent.slice(0, 5)));
}

function initCommandPalette() {
  /* Record current page in recently-visited */
  var currentMod = FH_MODULES.find(function(m) {
    return m.active && m.url && window.location.pathname.replace(/\/$/, '') === m.url.replace(/\/$/, '');
  });
  if (currentMod) _fhRecordVisit(currentMod.url);

  var ov      = document.getElementById('fh-cmd-ov');
  var input   = document.getElementById('fh-cmd-input');
  var results = document.getElementById('fh-cmd-results');
  var btn     = document.getElementById('fh-cmd-btn');
  if (!ov || !input || !results) return;

  var activeIdx = 0;

  function open() {
    ov.classList.add('open');
    input.value = '';
    render('');
    input.focus();
  }
  function close() {
    ov.classList.remove('open');
  }

  function render(query) {
    results.innerHTML = '';
    query = query.trim().toLowerCase();
    var allItems = [];

    if (!query) {
      var recentUrls  = _fhGetRecent().slice(0, 3);
      var recentMods  = recentUrls.map(function(u) {
        return FH_MODULES.find(function(m) { return m.url === u; });
      }).filter(Boolean);

      if (recentMods.length) {
        results.appendChild(_section('TERAKHIR DIKUNJUNGI'));
        recentMods.forEach(function(m) {
          var el = _item(m);
          results.appendChild(el);
          if (m.active) allItems.push(el);
        });
      }
      results.appendChild(_section('SEMUA MODUL'));
      var active   = FH_MODULES.filter(function(m) { return m.active; });
      var inactive = FH_MODULES.filter(function(m) { return !m.active; });
      active.forEach(function(m) {
        var el = _item(m);
        results.appendChild(el);
        allItems.push(el);
      });
      if (inactive.length) {
        var sep = document.createElement('div');
        sep.className = 'fh-cmd-sep';
        results.appendChild(sep);
        inactive.forEach(function(m) { results.appendChild(_item(m)); });
      }
    } else {
      var matched = FH_MODULES.filter(function(m) {
        return m.name.toLowerCase().indexOf(query) !== -1;
      });
      if (!matched.length) {
        var empty = document.createElement('div');
        empty.className = 'fh-cmd-empty';
        empty.textContent = 'Tidak ada modul ditemukan.';
        results.appendChild(empty);
      } else {
        results.appendChild(_section('HASIL PENCARIAN'));
        matched.forEach(function(m) {
          var el = _item(m);
          results.appendChild(el);
          if (m.active) allItems.push(el);
        });
      }
    }
    setActive(0, allItems);
  }

  function _section(label) {
    var el = document.createElement('div');
    el.className = 'fh-cmd-section';
    el.textContent = label;
    return el;
  }

  function _item(mod) {
    var el = document.createElement('div');
    el.className = 'fh-cmd-item' + (mod.active ? '' : ' disabled');
    el.innerHTML = '<span>' + mod.name + '</span>' +
      (!mod.active ? '<span class="fh-cmd-badge">Coming Soon</span>' : '');
    if (mod.active && mod.url) {
      el.addEventListener('click', function() {
        _fhRecordVisit(mod.url);
        close();
        window.location.href = mod.url;
      });
    }
    return el;
  }

  function getActiveEls() {
    return Array.from(results.querySelectorAll('.fh-cmd-item:not(.disabled)'));
  }

  function setActive(idx, items) {
    items = items || getActiveEls();
    if (!items.length) return;
    activeIdx = Math.max(0, Math.min(idx, items.length - 1));
    items.forEach(function(el, i) { el.classList.toggle('active', i === activeIdx); });
    var active = items[activeIdx];
    if (active) active.scrollIntoView({ block: 'nearest' });
  }

  input.addEventListener('input', function() { render(input.value); });

  document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      ov.classList.contains('open') ? close() : open();
      return;
    }
    if (!ov.classList.contains('open')) return;
    if (e.key === 'Escape')    { e.preventDefault(); close(); }
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(activeIdx + 1); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setActive(activeIdx - 1); }
    if (e.key === 'Enter') {
      e.preventDefault();
      var items = getActiveEls();
      if (items[activeIdx]) items[activeIdx].click();
    }
  });

  ov.addEventListener('click', function(e) { if (e.target === ov) close(); });
  if (btn) btn.addEventListener('click', open);
}

/* ── Skeleton loading ──────────────────────────────────── */
function skeletonRows(cols, count) {
  count = count || 6;
  return Array(count).fill(0).map(function() {
    return '<tr class="fh-skel-row">' +
      Array(cols).fill(0).map(function(_, i) {
        return '<td><div class="fh-skel" style="width:' + (55 + (i * 17) % 35) + '%"></div></td>';
      }).join('') +
      '</tr>';
  }).join('');
}

/* ── Sortable columns (DOM-based) ──────────────────────── */
function makeSortable(tableId) {
  var table = document.getElementById(tableId);
  if (!table || table.dataset.sortable) return;
  table.dataset.sortable = '1';

  var sortCol = -1, sortAsc = true;

  table.querySelectorAll('thead th[data-sort]').forEach(function(th) {
    var colIdx = parseInt(th.dataset.sort, 10);
    var isNum  = th.dataset.sortType === 'num';
    th.style.cursor = 'pointer';
    th.addEventListener('click', function() {
      if (sortCol === colIdx) { sortAsc = !sortAsc; } else { sortCol = colIdx; sortAsc = true; }
      table.querySelectorAll('thead th[data-sort]').forEach(function(h) {
        h.dataset.sortDir = parseInt(h.dataset.sort, 10) === sortCol
          ? (sortAsc ? 'asc' : 'desc') : '';
      });
      var tbody = table.querySelector('tbody');
      var rows  = Array.from(tbody.querySelectorAll('tr:not(.fh-skel-row):not(.pam-detail-row)'));
      rows.sort(function(a, b) {
        var va = (a.cells[colIdx] ? a.cells[colIdx].textContent : '').trim();
        var vb = (b.cells[colIdx] ? b.cells[colIdx].textContent : '').trim();
        var na = isNum ? (parseFloat(va.replace(/[.,\s]/g,'')) || 0) : va.toLowerCase();
        var nb = isNum ? (parseFloat(vb.replace(/[.,\s]/g,'')) || 0) : vb.toLowerCase();
        return sortAsc ? (na > nb ? 1 : -1) : (na < nb ? 1 : -1);
      });
      rows.forEach(function(r) { tbody.appendChild(r); });
    });
  });
}

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
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = type === "success" ? "toast-success" : type === "info" ? "toast-info" : "toast-error";
  toast.style.opacity = "1";
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { toast.style.opacity = "0"; }, 3000);
}

function openModal(id) { const el = document.getElementById(id); if (el) el.classList.add("open"); }
function closeModal(id) { const el = document.getElementById(id); if (el) el.classList.remove("open"); }

function staggerRows(tbody) {
  Array.from(tbody.querySelectorAll("tr")).forEach((row, i) => {
    row.classList.add("stagger-row");
    row.style.animationDelay = `${i * 28}ms`;
    row.style.animationFillMode = "both";
  });
}

function animateCounter(el, duration = 700) {
  const target = parseFloat(el.dataset.count);
  if (isNaN(target) || target === 0) return;
  const prefix = el.dataset.prefix || "";
  const fmt = new Intl.NumberFormat("id-ID");
  const start = performance.now();
  const step = (now) => {
    const p = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    el.textContent = prefix + fmt.format(Math.round(ease * target));
    if (p < 1) requestAnimationFrame(step);
    else el.textContent = prefix + fmt.format(target);
  };
  requestAnimationFrame(step);
}

document.addEventListener("DOMContentLoaded", () => {
  initCommandPalette();
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", e => { if (e.target === overlay) overlay.classList.remove("open"); });
  });
  document.querySelectorAll("tbody").forEach(staggerRows);
  document.querySelectorAll(".stat-value[data-count]").forEach(el => animateCounter(el));
});
