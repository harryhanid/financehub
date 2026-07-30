/* ── Module registry ──────────────────────────────────── */
const FH_MODULES = [
  { name: "Dashboard",             url: "/dashboard",               active: true  },
  { name: "Beasiswa",              url: "/beasiswa",                active: true  },
  { name: "Payment Approval Memo", url: "/payment-memo",            active: true  },
  { name: "Payment Application",   url: "/etf-payment-application", active: true  },
  { name: "Budget",                url: "/budget/",                 active: true  },
  { name: "Users",                 url: "/users",                   active: true  },
  { name: "Bank",                  url: "/bank",                    active: true  },
  { name: "Account Payable",       url: null,                       active: false },
  { name: "Advance",               url: null,                       active: false },
  { name: "Petty Cash",            url: null,                       active: false },
  { name: "Sponsorship",           url: "/sponsorship/",            active: true  },
];
const FH_RECENT_KEY = 'fh_recent_modules';

// Company-filtered module list + sub-tab previews for the Alt+Down carousel,
// rendered server-side by inject_nav_modules() in app.py — see base.html's
// #fh-nav-modules-data script tag. Read once at load; server always injects
// this tag (nav_modules is always in template context, empty list when
// logged out), so this never needs to re-fetch.
const FH_NAV_MODULES = (function() {
  var el = document.getElementById('fh-nav-modules-data');
  if (!el) return [];
  try { return JSON.parse(el.textContent); } catch (e) { return []; }
})();

// One small flow-line-style icon per real module, keyed by nav_modules' `key`.
const FH_MODULE_ICONS = {
  dashboard: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  beasiswa: '<path d="M12 3 2 8l10 5 10-5-10-5Z"/><path d="M6 10.5V16c0 1.5 3 3 6 3s6-1.5 6-3v-5.5"/>',
  payment_memo: '<path d="M6 2h9l4 4v16H6Z"/><path d="M15 2v4h4"/><path d="M9 13l2 2 4-4"/>',
  etf_payment_app: '<path d="M6 2h8l5 5v15H6Z"/><path d="M14 2v5h5"/><path d="M12 12v6M9 15l3-3 3 3"/>',
  budget: '<path d="M12 12V4a8 8 0 0 1 8 8h-8Z"/><circle cx="12" cy="12" r="8"/>',
  bank: '<path d="M3 10l9-6 9 6"/><path d="M5 10v9M9 10v9M15 10v9M19 10v9"/><path d="M3 21h18"/>',
  sponsorship: '<rect x="3" y="8" width="18" height="13" rx="1"/><path d="M3 12h18"/><path d="M12 8v13"/><path d="M12 8c-1.5-4-6-4-6-1s3 1 6 1Zm0 0c1.5-4 6-4 6-1s-3 1-6 1Z"/>',
  users: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
};

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
  /* Record current page in recently-visited (kept for possible future use —
     the carousel itself has no "recently visited" section, see spec). */
  var currentMod = getCurrentModule();
  if (currentMod) _fhRecordVisit(currentMod.url);

  var ov       = document.getElementById('fh-cmd-ov');
  var input    = document.getElementById('fh-cmd-input');
  var track    = document.getElementById('fh-cmd-track');
  var dotsEl   = document.getElementById('fh-cmd-dots');
  var prevBtn  = document.getElementById('fh-cmd-prev');
  var nextBtn  = document.getElementById('fh-cmd-next');
  var btn      = document.getElementById('fh-cmd-btn');
  if (!ov || !input || !track || !dotsEl) return;

  var allModules       = _carouselModules();
  var filtered         = allModules;
  var activeIdx        = 0;
  var openCurrentMod   = null;   // the module the user was in when they opened the overlay
  var openCurrentTab   = null;   // its ?tab= value at open time, if any
  var dragStartX       = null;

  function _carouselModules() {
    var comingSoon = FH_MODULES.filter(function(m) { return !m.active; }).map(function(m) {
      return { name: m.name, url: null, key: null, subtabs: [], active: false };
    });
    var real = FH_NAV_MODULES.map(function(m) {
      return { name: m.name, url: m.url, key: m.key, subtabs: m.subtabs || [], active: true };
    });
    return real.concat(comingSoon);
  }

  function _currentNavModule() {
    return FH_NAV_MODULES.find(function(m) {
      return window.location.pathname.replace(/\/$/, '') === m.url.replace(/\/$/, '');
    });
  }

  function open() {
    filtered = allModules;
    openCurrentMod = _currentNavModule();
    openCurrentTab = new URLSearchParams(window.location.search).get('tab');
    activeIdx = 0;
    if (openCurrentMod) {
      var found = filtered.findIndex(function(m) { return m.key === openCurrentMod.key; });
      if (found !== -1) activeIdx = found;
    }
    input.value = '';
    ov.classList.add('open');
    render();
    input.focus();
  }
  function close() {
    ov.classList.remove('open');
  }

  function step(delta) {
    if (!filtered.length) return;
    activeIdx = (activeIdx + delta + filtered.length) % filtered.length;
    render();
  }

  function _openModule(mod) {
    if (!mod || !mod.active || !mod.url) return;
    _fhRecordVisit(mod.url);
    close();
    window.location.href = mod.url;
  }

  function _openSubtab(mod, t) {
    var dest = t.url || (mod.url + (mod.url.indexOf('?') === -1 ? '?' : '&') + 'tab=' + t.tab);
    _fhRecordVisit(mod.url);
    close();
    window.location.href = dest;
  }

  function _isActiveTab(mod, t) {
    if (!openCurrentMod || mod.key !== openCurrentMod.key) return false;
    if (t.url) return window.location.pathname.replace(/\/$/, '') === t.url.replace(/\/$/, '');
    var defaultTab = mod.subtabs.length ? mod.subtabs[0].tab : null;
    return t.tab === (openCurrentTab || defaultTab);
  }

  function _card(mod, isMain) {
    var outer = document.createElement('div');
    outer.className = isMain ? 'fh-cmd-card-main' : 'fh-cmd-card-side';

    var bezel = document.createElement('div');
    bezel.className = 'fh-cmd-card-outer';
    var inner = document.createElement('div');
    inner.className = 'fh-cmd-card-inner';

    if (mod.key) {
      var icon = document.createElement('div');
      icon.className = 'fh-cmd-icon';
      icon.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + (FH_MODULE_ICONS[mod.key] || '') + '</svg>';
      inner.appendChild(icon);
    }

    var name = document.createElement('div');
    name.className = 'fh-cmd-card-name';
    name.textContent = mod.name;
    inner.appendChild(name);

    if (!mod.active) {
      var badge = document.createElement('div');
      badge.className = 'fh-cmd-badge';
      badge.textContent = 'Coming Soon';
      inner.appendChild(badge);
    } else if (isMain && mod.subtabs.length) {
      var line = document.createElement('div');
      line.className = 'fh-cmd-tabline';
      inner.appendChild(line);
      mod.subtabs.forEach(function(t) {
        var row = document.createElement('div');
        row.className = 'fh-cmd-tab' + (_isActiveTab(mod, t) ? ' active' : '');
        row.textContent = t.label;
        row.addEventListener('click', function(e) {
          e.stopPropagation();
          _openSubtab(mod, t);
        });
        inner.appendChild(row);
      });
    }

    if (mod.active && mod.url) {
      outer.style.cursor = 'pointer';
      outer.addEventListener('click', function() {
        if (isMain) { _openModule(mod); }
        else { activeIdx = filtered.indexOf(mod); render(); }
      });
    }

    bezel.appendChild(inner);
    outer.appendChild(bezel);
    return outer;
  }

  function render() {
    track.innerHTML = '';
    dotsEl.innerHTML = '';
    if (!filtered.length) {
      var empty = document.createElement('div');
      empty.className = 'fh-cmd-empty';
      empty.textContent = 'Tidak ada modul ditemukan.';
      track.appendChild(empty);
      return;
    }
    activeIdx = Math.max(0, Math.min(activeIdx, filtered.length - 1));
    for (var i = -1; i <= 1; i++) {
      var idx = activeIdx + i;
      if (idx < 0 || idx >= filtered.length) continue;
      track.appendChild(_card(filtered[idx], i === 0));
    }
    filtered.forEach(function(m, i) {
      var dot = document.createElement('span');
      if (i === activeIdx) dot.className = 'on';
      dotsEl.appendChild(dot);
    });
  }

  input.addEventListener('input', function() {
    var q = input.value.trim().toLowerCase();
    filtered = q ? allModules.filter(function(m) { return m.name.toLowerCase().indexOf(q) !== -1; }) : allModules;
    activeIdx = 0;
    render();
  });

  if (prevBtn) prevBtn.addEventListener('click', function() { step(-1); });
  if (nextBtn) nextBtn.addEventListener('click', function() { step(1); });

  track.addEventListener('pointerdown', function(e) { dragStartX = e.clientX; });
  track.addEventListener('pointerup', function(e) {
    if (dragStartX === null) return;
    var dx = e.clientX - dragStartX;
    dragStartX = null;
    if (dx > 40) step(-1); else if (dx < -40) step(1);
  });

  document.addEventListener('keydown', function(e) {
    if (e.altKey && !e.ctrlKey && !e.metaKey && e.key === 'ArrowDown') {
      e.preventDefault();
      ov.classList.contains('open') ? close() : open();
      return;
    }
    if (!ov.classList.contains('open')) return;
    if (e.key === 'Escape')     { e.preventDefault(); close(); }
    if (e.key === 'ArrowLeft')  { e.preventDefault(); step(-1); }
    if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
    if (e.key === 'Enter') {
      e.preventDefault();
      _openModule(filtered[activeIdx]);
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

function initModuleSwitchDropdown() {
  var trigger = document.getElementById('fh-mod-trigger');
  var panel   = document.getElementById('fh-mod-dd');
  if (!trigger || !panel) return;

  function open() {
    panel.classList.add('open');
    trigger.setAttribute('aria-expanded', 'true');
  }
  function close() {
    panel.classList.remove('open');
    trigger.setAttribute('aria-expanded', 'false');
  }
  function toggle(e) {
    e.stopPropagation();
    if (panel.classList.contains('open')) close(); else open();
  }

  trigger.addEventListener('click', toggle);
  trigger.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(e); }
    else if (e.key === 'Escape') { close(); }
  });
  panel.querySelectorAll('.fh-mod-dd-item[data-url]').forEach(function(item) {
    item.addEventListener('click', function() {
      window.location.href = item.dataset.url;
    });
  });
  document.addEventListener('click', function(e) {
    if (!trigger.contains(e.target) && !panel.contains(e.target)) close();
  });
}

function initHeaderTabFade() {
  document.querySelectorAll('.navbar-menu').forEach(function(el) {
    function update() {
      var atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 1;
      el.classList.toggle('fh-overflow', el.scrollWidth > el.clientWidth + 1 && !atEnd);
    }
    update();
    el.addEventListener('scroll', update);
    window.addEventListener('resize', update);
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
  // Tab buttons now live in the navbar's module_tabs block (unified-header
  // migration), outside `container` ([data-tabs], which only wraps the
  // .tab-panel content) — a container-scoped query here always finds zero
  // buttons, silently skipping every listener attach and the auto-activate
  // call below, leaving every panel without .active (blank page). Query
  // globally instead, matching pressTabStep()'s existing '.tabs .tab-btn'
  // selector, since each page has exactly one such button group.
  const tabs = document.querySelectorAll(".tabs .tab-btn");
  const panels = container.querySelectorAll(".tab-panel");
  const filterBtn = container.querySelector(".btn-filter-toggle");
  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      panels.forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const target = container.querySelector(`#${btn.dataset.tab}`);
      if (target) target.classList.add("active");
      // Sync the active tab into the URL (no reload) so a save action that
      // triggers location.reload()/window.location.reload() while on a
      // non-first tab lands back on the same tab instead of silently
      // resetting to the first one on next page load.
      const tabName = btn.dataset.tab.replace(/^tab-/, "");
      const url = new URL(window.location);
      url.searchParams.set("tab", tabName);
      history.replaceState(null, "", url);
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
  // Deep-link support: ?tab=<name> selects [data-tab="tab-<name>"] instead
  // of always defaulting to the first tab — used by redirects like
  // /beasiswa/sahabat -> /beasiswa/?tab=sahabat. Falls back to today's
  // default behavior when absent or no match is found.
  const requestedTab = new URLSearchParams(window.location.search).get("tab");
  const requested = requestedTab && container.querySelector(`[data-tab="tab-${requestedTab}"]`);
  if (requested) {
    requested.click();
  } else if (tabs.length > 0) {
    tabs[0].click();
  }
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

function showLoading(msg) {
  let el = document.getElementById("fh-load-ov");
  if (!el) {
    el = document.createElement("div");
    el.id = "fh-load-ov";
    el.innerHTML = `<div class="fh-load-card"><div class="fh-load-spin"></div><div class="fh-load-msg"></div></div>`;
    document.body.appendChild(el);
  }
  el.querySelector(".fh-load-msg").textContent = msg || "Memuat...";
  el.classList.add("show");
}

function hideLoading() {
  const el = document.getElementById("fh-load-ov");
  if (el) el.classList.remove("show");
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
  if (open && window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
    const searchInput = panel.querySelector('input[type="text"]');
    if (searchInput) searchInput.focus();
  }
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

// Global shortcuts: F toggles the filter panel, Alt+←/→ steps tabs, Alt+↑
// opens Ganti Perusahaan. Skipped entirely while focus is in a typing field
// so normal typing (including the letter "f") is never hijacked — see
// docs/superpowers/specs/2026-07-13-financehub-keyboard-shortcuts-design.md §2.2
document.addEventListener('keydown', e => {
  const el = document.activeElement;
  const typing = el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable);
  if (typing) return;
  if (e.altKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
    e.preventDefault();
    pressTabStep(e.key === 'ArrowRight' ? 1 : -1);
  } else if (e.altKey && e.key === 'ArrowUp') {
    const companyLink = document.querySelector('.navbar-company');
    if (companyLink) { e.preventDefault(); companyLink.click(); }
  } else if (!e.altKey && !e.ctrlKey && !e.metaKey && e.key.toLowerCase() === 'f') {
    e.preventDefault();
    document.querySelector('.btn-filter-toggle')?.click();
  }
});

document.addEventListener("DOMContentLoaded", () => {
  initCommandPalette();
  initTitleDropdown();
  initModuleSwitchDropdown();
  initHeaderTabFade();
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", e => { if (e.target === overlay) overlay.classList.remove("open"); });
  });
  document.querySelectorAll("tbody").forEach(staggerRows);
  document.querySelectorAll(".stat-value[data-count]").forEach(el => animateCounter(el));
});
