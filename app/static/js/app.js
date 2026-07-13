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

/* Always block the browser's native Ctrl/Cmd+K (focus omnibox) first, in the
   capture phase — runs before any page-specific script can stopPropagation
   during the bubble phase, and before initCommandPalette() has even wired up
   (so it works even on pages where the palette DOM/JS fails for any reason). */
document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
    e.preventDefault();
  }
}, true);

function _fhGetRecent() {
  try { return JSON.parse(localStorage.getItem(FH_RECENT_KEY) || '[]'); } catch (e) { return []; }
}
function _fhRecordVisit(url) {
  if (!url) return;
  var recent = _fhGetRecent().filter(function(u) { return u !== url; });
  recent.unshift(url);
  localStorage.setItem(FH_RECENT_KEY, JSON.stringify(recent.slice(0, 5)));
}

function getCurrentModule() {
  return FH_MODULES.find(function(m) {
    return m.active && m.url && window.location.pathname.replace(/\/$/, '') === m.url.replace(/\/$/, '');
  });
}

function initCommandPalette() {
  /* Record current page in recently-visited */
  var currentMod = getCurrentModule();
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

function initTitleDropdown() {
  var cmdBtn = document.getElementById('fh-cmd-btn');
  if (!cmdBtn) return; // no company context on this page (e.g. login, select-company)

  var titleEl = document.querySelector('.main h1');
  if (!titleEl || titleEl.classList.contains('fh-title-trigger')) return;

  var activeMods = FH_MODULES.filter(function(m) { return m.active; });
  if (activeMods.length < 2) return; // nothing to switch to

  var currentMod = getCurrentModule();

  /* Wrap the h1 so the dropdown panel can position itself relative to
     just the title's box, not the full-width row it usually sits in. */
  var wrap = document.createElement('div');
  wrap.className = 'fh-title-wrap';
  titleEl.parentNode.insertBefore(wrap, titleEl);
  wrap.appendChild(titleEl);

  titleEl.classList.add('fh-title-trigger');
  titleEl.setAttribute('role', 'button');
  titleEl.setAttribute('tabindex', '0');
  titleEl.setAttribute('aria-haspopup', 'listbox');
  titleEl.setAttribute('aria-expanded', 'false');

  var chevron = document.createElement('span');
  chevron.className = 'fh-title-chevron';
  chevron.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
  titleEl.appendChild(chevron);

  var panel = document.createElement('div');
  panel.className = 'fh-title-dd';
  panel.setAttribute('role', 'listbox');

  activeMods.forEach(function(m) {
    var isCurrent = !!currentMod && m.url === currentMod.url;
    var item = document.createElement('div');
    item.className = 'fh-title-dd-item' + (isCurrent ? ' current' : '');
    item.setAttribute('role', 'option');
    item.innerHTML = '<span>' + m.name + '</span>' + (isCurrent
      ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
      : '');
    if (!isCurrent) {
      item.addEventListener('click', function() {
        _fhRecordVisit(m.url);
        window.location.href = m.url;
      });
    }
    panel.appendChild(item);
  });
  wrap.appendChild(panel);

  function open() {
    panel.classList.add('open');
    titleEl.setAttribute('aria-expanded', 'true');
  }
  function close() {
    panel.classList.remove('open');
    titleEl.setAttribute('aria-expanded', 'false');
  }
  function toggle(e) {
    e.stopPropagation();
    if (panel.classList.contains('open')) close(); else open();
  }

  titleEl.addEventListener('click', toggle);
  titleEl.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(e); }
    else if (e.key === 'Escape') { close(); }
  });
  document.addEventListener('click', function(e) {
    if (!wrap.contains(e.target)) close();
  });
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
  const filterBtn = container.querySelector(".btn-filter-toggle");
  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      panels.forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const target = container.querySelector(`#${btn.dataset.tab}`);
      if (target) target.classList.add("active");
      // Filter panel always starts collapsed when switching sub-modules —
      // see docs/superpowers/specs/2026-07-12-financehub-page-toolbar-layout-design.md §2.3
      container.querySelectorAll(".filter-bar.collapsible.open").forEach(p => p.classList.remove("open"));
      if (filterBtn) {
        filterBtn.classList.remove("active");
        updateFilterBadge(filterBtn.id, 0);
        // Hide the Filter toggle entirely on tabs with no filter panel (e.g. a
        // single-record detail/report tab) instead of leaving an inert button.
        const hasFilterPanel = !!(target && target.querySelector(".filter-bar.collapsible"));
        filterBtn.style.display = hasFilterPanel ? "" : "none";
      }
      // Newly-active panel's own scroll-height wrapper (if any) was hidden a
      // moment ago and may have a stale computed height — modules that size
      // their table wrap dynamically (e.g. sizeWrap()-style code) already
      // listen for "resize", so re-dispatch it once the new panel is visible.
      window.dispatchEvent(new Event("resize"));
    });
  });
  if (filterBtn) {
    container.querySelectorAll(".filter-bar.collapsible").forEach(panel => {
      const recompute = () => refreshFilterBadge(panel, filterBtn.id);
      panel.addEventListener("input", recompute);
      panel.addEventListener("change", recompute);
    });
  }
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
    row.style.animationDelay = `${Math.min(i, 20) * 28}ms`;
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

function toggleFilterPanel(panelId, btnId) {
  const panel = document.getElementById(panelId);
  const btn = document.getElementById(btnId);
  if (!panel) return;
  const open = panel.classList.toggle("open");
  if (btn) btn.classList.toggle("active", open);
}

// Toggle the .filter-bar.collapsible panel belonging to the currently active
// .tab-panel inside `container` (a [data-tabs] element) — for modules with one
// filter row per tab (Beasiswa, Payment Memo) instead of a single shared
// filter row like ETF PA (which uses toggleFilterPanel(panelId, btnId) directly).
function toggleActiveTabFilter(container, btnId) {
  if (!container) return;
  const activePanel = container.querySelector(".tab-panel.active");
  const panel = activePanel && activePanel.querySelector(".filter-bar.collapsible");
  if (!panel) return;
  if (!panel.id) panel.id = "fh-tab-filter-" + Math.random().toString(36).slice(2, 8);
  toggleFilterPanel(panel.id, btnId);
}

// Recomputes a filter-toggle badge from how many inputs/selects inside `panel`
// currently hold a non-empty value — generic so per-module filter fields don't
// need to be hardcoded (relies on the existing "empty-string = Semua ..." default
// option convention already used throughout FinanceHub's filter dropdowns).
function refreshFilterBadge(panel, btnId) {
  if (!panel) return;
  let n = 0;
  panel.querySelectorAll("input, select").forEach(el => {
    if (el.type === "checkbox" || el.type === "radio") return;
    if ((el.value || "").trim() !== "") n++;
  });
  updateFilterBadge(btnId, n);
}

function updateFilterBadge(btnId, count) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  let badge = btn.querySelector(".filter-badge");
  if (count > 0) {
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "filter-badge";
      btn.appendChild(badge);
    }
    badge.textContent = count;
  } else if (badge) {
    badge.remove();
  }
}

function enterFocusMode() {
  document.body.classList.add('fh-focus');
  setTimeout(() => window.dispatchEvent(new Event('resize')), 240); // wait for navbar collapse transition
}
function exitFocusMode() {
  document.body.classList.remove('fh-focus');
  setTimeout(() => window.dispatchEvent(new Event('resize')), 240);
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && document.body.classList.contains('fh-focus')) exitFocusMode();
});

// Steps the active .tab-btn within `.tabs` by `delta` positions (wraps around
// at either end) and clicks the resulting tab. Works for both server-rendered
// <a href> tabs (ETF PA — .click() navigates) and client-side <button
// data-tab> tabs (Payment Memo/Beasiswa — .click() triggers initTabs()'s own
// listener) since it delegates to whatever the tab element already does.
function pressTabStep(delta) {
  const tabs = [...document.querySelectorAll('.tabs .tab-btn')];
  if (!tabs.length) return;
  const activeIdx = tabs.findIndex(t => t.classList.contains('active'));
  const from = activeIdx === -1 ? 0 : activeIdx;
  const next = (from + delta + tabs.length) % tabs.length;
  tabs[next].click();
}

// Global shortcuts: F toggles the filter panel, Alt+←/→ steps tabs. Skipped
// entirely while focus is in a typing field so normal typing (including the
// letter "f") is never hijacked — see docs/superpowers/specs/2026-07-13-financehub-keyboard-shortcuts-design.md §2.2
document.addEventListener('keydown', e => {
  const el = document.activeElement;
  const typing = el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable);
  if (typing) return;
  if (e.altKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
    e.preventDefault();
    pressTabStep(e.key === 'ArrowRight' ? 1 : -1);
  } else if (!e.altKey && !e.ctrlKey && !e.metaKey && e.key.toLowerCase() === 'f') {
    e.preventDefault();
    document.querySelector('.btn-filter-toggle')?.click();
  }
});

document.addEventListener("DOMContentLoaded", () => {
  initCommandPalette();
  initTitleDropdown();
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", e => { if (e.target === overlay) overlay.classList.remove("open"); });
  });
  document.querySelectorAll("tbody").forEach(staggerRows);
  document.querySelectorAll(".stat-value[data-count]").forEach(el => animateCounter(el));
});
