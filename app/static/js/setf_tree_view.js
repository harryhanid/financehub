// Renderer DOM Tree Query Sahabat ETF (kartu bertumpuk, garis bloodline klasik).
// Logika ada di setf_tree_model.js.
(function (root) {
  const M = root.SetfTreeModel;
  let host = null;
  let roots = [];
  let idx = null;
  let openIds = new Set();
  let revealed = new Set();
  let mode = 'default';
  let query = '';
  let picked = null;
  let bound = false;

  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function statusEl() { return document.getElementById('tree-status'); }
  function setStatus(html) { const el = statusEl(); if (el) el.innerHTML = html; }

  function tooltip(node) {
    const lines = [node.name + (node.id ? ' | ' + node.id : '')];
    if (node.tanggal_lahir) lines.push('Tanggal Lahir: ' + node.tanggal_lahir);
    if (node.catatan) lines.push('Catatan: ' + node.catatan);
    (node.partners || []).forEach((p) => {
      lines.push('');
      lines.push(p.name + ' (Partner) | ' + (p.id || ''));
      if (p.tanggal_lahir) lines.push('Tanggal Lahir: ' + p.tanggal_lahir);
      if (p.catatan) lines.push('Catatan: ' + p.catatan);
    });
    return lines.join('\n');
  }

  function partnerHtml(p, hitIds) {
    const code = p.id ? p.id.split('.').pop().toUpperCase() : '';
    const cls = hitIds && hitIds.indexOf(p.id) >= 0 ? ' hit' : '';
    return '<div class="tr-partner' + cls + '">' + esc(p.name) + ' (Partner' + (code ? ' ' + code : '') + ')</div>';
  }

  function cardHtml(row, opts) {
    opts = opts || {};
    const node = row.node;
    const classes = ['tr-card'];
    if (opts.toggle && row.hasChildren) classes.push('clickable');
    if (row.open) classes.push('open');
    if (row.isHit) classes.push('hit');
    else if (opts.path) classes.push('path');
    if (opts.extra) classes.push(opts.extra);
    const code = node.id && !/^[A-Za-z]$/.test(node.id) ? '<span class="tr-code">(' + esc(node.id) + ')</span>' : '';
    const caret = opts.toggle && row.hasChildren
      ? '<span class="tr-caret">' + (row.open ? '▾' : '▸') + ' ' + row.childCount + '</span>' : '';
    const partners = (node.partners || []).map((p) => partnerHtml(p, row.partnerHitIds)).join('');
    const data = opts.toggle && row.hasChildren ? ' data-toggle="' + esc(row.id) + '"' : '';
    return '<div class="' + classes.join(' ') + '"' + data + ' title="' + esc(tooltip(node)) + '">'
      + caret + '<span class="tr-name">' + esc(node.name) + '</span>' + code + partners + '</div>';
  }

  // Baris datar (dengan indent) -> daftar bersarang; tiap tingkat punya batang garis sendiri.
  function stackHtml(rows) {
    let i = 0;
    function level(ind) {
      let h = '';
      while (i < rows.length && rows[i].indent === ind) {
        const r = rows[i++];
        const badge = r.badge ? '<div class="tr-badgewrap"><span class="tr-badge">' + r.badge + '</span></div>' : '';
        let sub = '';
        if (i < rows.length && rows[i].indent > ind) sub = '<div class="tr-stack">' + level(ind + 1) + '</div>';
        h += badge + '<div class="tr-item">' + cardHtml(r, { toggle: true }) + sub + '</div>';
      }
      return h;
    }
    return level(0);
  }

  function pickerHtml() {
    const pills = roots.map((r) =>
      '<button type="button" class="tr-pill' + (picked === r.id ? ' on' : '') + '" data-pick="' + esc(r.id) + '" title="'
      + esc(r.name) + '">Cabang ' + esc(r.id) + '</button>').join('');
    return '<div class="tr-picker"><span>Pilih cabang:</span>' + pills + '</div>';
  }

  function defaultHtml() {
    const sel = roots.filter((r) => r.id === picked);
    if (!sel.length) {
      return pickerHtml() + '<div class="tr-empty">Pilih cabang (' + roots.map((r) => esc(r.id)).join(', ') + ') untuk menampilkan tree.</div>';
    }
    const block = M.buildColumns(sel, openIds)[0];
    const rootRow = { node: block.root, id: block.root.id, open: false, hasChildren: false, childCount: 0, partnerHitIds: [] };
    const cols = block.columns.map((col) =>
      '<div class="tr-c">' + cardHtml(col.g1, { toggle: false, extra: 'tr-g1card' })
      + (col.rows.length ? '<div class="tr-stack tr-trunk">' + stackHtml(col.rows) + '</div>' : '') + '</div>').join('');
    return pickerHtml() + '<div class="tr-export"><div class="tr-block"><div class="tr-body">'
      + '<div class="tr-ruler"><div class="tr-ruler-cell" data-g1label="1">G1</div></div>'
      + '<div class="tr-tree">' + cardHtml(rootRow, { toggle: false, extra: 'tr-rootcard' })
      + (block.columns.length ? '<div class="tr-stem"></div><div class="tr-row">' + cols + '</div>' : '')
      + '</div></div></div></div>';
  }

  function focusHtml(blocks) {
    return '<div class="tr-export">' + blocks.map((b) => {
      const chainIds = new Set(b.chain.map((r) => r.id).concat([b.root.id]));
      const rows = b.chain.map((r) => {
        let sibs = '';
        let chip = '';
        if (r.hiddenSiblings > 0) {
          if (revealed.has(r.id)) {
            const parent = idx.byId.get(r.id);
            const kids = parent && parent.parentId ? idx.byId.get(parent.parentId).node.children : [];
            sibs = kids.filter((k) => !chainIds.has(k.id)).map((k) =>
              cardHtml({ node: k, id: k.id, open: false, hasChildren: false, childCount: 0, partnerHitIds: [] }, { extra: 'tr-sib' })).join('');
          } else {
            chip = '<span class="tr-chip" data-reveal="' + esc(r.id) + '">+ ' + r.hiddenSiblings + ' saudara</span>';
          }
        }
        const canOpen = r.hasChildren && r.focusChildren === 0;
        const open = canOpen && openIds.has(r.id);
        const row = Object.assign({}, r, { open });
        const kids = open
          ? '<div class="tr-stack tr-trunk">' + stackHtml(M.childRows(r.node, r.gen, openIds)) + '</div>' : '';
        return '<div class="tr-chainrow"><div class="tr-ruler"><div class="tr-ruler-cell">' + r.ruler + '</div></div>'
          + '<div class="tr-chainbody" style="--g:' + r.gen + '"><div class="tr-chaininline">'
          + cardHtml(row, { path: true, toggle: canOpen }) + chip + sibs + '</div>' + kids + '</div></div>';
      }).join('');
      return '<div class="tr-block"><div class="tr-block-head"><div class="tr-root-card">'
        + cardHtml(b.root, { path: true }) + '</div></div>' + rows + '</div>';
    }).join('') + '</div>';
  }

  // Label G1 sejajar dengan baris kartu G1 (posisi tergantung tinggi kartu akar).
  function placeRulers() {
    if (!host) return;
    host.querySelectorAll('.tr-body').forEach((body) => {
      const g1 = body.querySelector('.tr-g1card');
      const lab = body.querySelector('[data-g1label]');
      if (!g1 || !lab) return;
      const top = g1.getBoundingClientRect().top - body.getBoundingClientRect().top;
      lab.style.marginTop = Math.max(0, top) + 'px';
      lab.style.height = g1.offsetHeight + 'px';
    });
  }

  function paint(html) {
    const wrap = document.getElementById('tree-wrapper');
    const st = wrap ? [wrap.scrollTop, wrap.scrollLeft] : [0, 0];
    host.innerHTML = html;
    placeRulers();
    if (wrap) { wrap.scrollTop = st[0]; wrap.scrollLeft = st[1]; }
  }

  function renderDefault() {
    mode = 'default';
    query = '';
    setStatus('');
    paint(defaultHtml());
  }

  function renderFocus(q) {
    const res = M.searchFocus(roots, q);
    if (!res) { renderDefault(); return; }
    mode = 'focus';
    query = q;
    if (!res.shownFamilies) {
      setStatus('Tidak ada hasil untuk "' + esc(q) + '". <a href="#" data-reset="1">Reset</a>');
      paint('<div class="tr-empty">Tidak ada hasil</div>');
      return;
    }
    setStatus('Menampilkan ' + res.shownFamilies + ' dari ' + res.totalFamilies
      + ' keluarga &middot; <a href="#" data-reset="1">Tampilkan semua</a>');
    paint(focusHtml(M.focusRows(res.families)));
  }

  function rerender() { if (mode === 'focus') renderFocus(query); else renderDefault(); }

  function reset() { openIds = new Set(); revealed = new Set(); renderDefault(); }

  function onClick(e) {
    const rs = e.target.closest('[data-reset]');
    if (rs) { e.preventDefault(); const inp = document.getElementById('tree-search-input'); if (inp) inp.value = ''; reset(); return; }
    const pk = e.target.closest('[data-pick]');
    if (pk) { picked = pk.getAttribute('data-pick'); openIds = new Set(); renderDefault(); return; }
    const rv = e.target.closest('[data-reveal]');
    if (rv) { revealed.add(rv.getAttribute('data-reveal')); renderFocus(query); return; }
    const tg = e.target.closest('[data-toggle]');
    if (tg) { openIds = M.toggleOpen(openIds, tg.getAttribute('data-toggle')); rerender(); }
  }

  function mount(container, data) {
    host = container;
    roots = data;
    idx = M.indexTree(roots);
    if (!bound) {
      bound = true;
      host.addEventListener('click', onClick);
      const st = statusEl();
      if (st) st.addEventListener('click', onClick);
    }
    reset();
  }

  function names() {
    const set = new Set();
    idx.byId.forEach((v) => {
      set.add(v.node.name);
      (v.node.partners || []).forEach((p) => set.add(p.name));
    });
    return Array.from(set).filter(Boolean).sort();
  }

  function setTextScale(mult) { host.style.setProperty('--tree-font', (12 * mult) + 'px'); placeRulers(); }
  function setSpacing(mult) {
    host.style.setProperty('--tree-gap', (14 * mult) + 'px');
    host.style.setProperty('--tree-indent', (14 * mult) + 'px');
    placeRulers();
  }
  function getExportElement() { return host.querySelector('.tr-export') || host; }
  function currentQuery() { return mode === 'focus' ? query : ''; }
  function hasContent() { return !!host.querySelector('.tr-export'); }

  root.SetfTreeView = { mount, renderDefault, renderFocus, reset, names, setTextScale, setSpacing, getExportElement, currentQuery, hasContent, rerender };
})(window);
