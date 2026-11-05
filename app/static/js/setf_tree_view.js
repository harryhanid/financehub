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
  let focusG1 = null;
  let wide = false;
  let wideA = false;
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
    const cls = hitIds && hitIds.indexOf(p.id) >= 0 ? ' hit' : '';
    return '<div class="tr-partner' + cls + '">' + esc(p.name) + ' (Partner)</div>';
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
    const caret = opts.toggle && row.hasChildren
      ? '<span class="tr-caret">' + (row.open ? '▾' : '▸') + ' ' + row.childCount + '</span>' : '';
    const partners = (node.partners || []).map((p) => partnerHtml(p, row.partnerHitIds)).join('');
    // G1 adalah pasangan (partner) dari kepala keluarga di akar
    const ptag = row.gen === 1 ? ' <span class="tr-ptag">(Partner)</span>' : '';
    const data = (opts.toggle && row.hasChildren ? ' data-toggle="' + esc(row.id) + '"' : '')
      + (opts.focus ? ' data-focus="' + esc(row.id) + '"' : '')
      + (opts.unfocus ? ' data-unfocus="1"' : '')
      + (opts.gen ? ' data-gen="' + esc(opts.gen) + '"' : '');
    // nomor urut = angka terakhir dari kode (A1.2 -> 2)
    let num = '';
    if (opts.num) {
      const m = /(\d+)\s*$/.exec(String(node.id || '').split('.').pop());
      if (m) num = '<span class="tr-num">' + parseInt(m[1], 10) + '</span>';
    }
    if (num) classes.push('has-num');
    return '<div class="' + classes.join(' ') + '"' + data + ' title="' + esc(tooltip(node)) + '">'
      + num + caret + '<span class="tr-name">' + esc(node.name) + '</span>' + ptag + partners + '</div>';
  }

  // Baris datar (dengan indent) -> daftar bersarang; tiap tingkat punya batang garis sendiri.
  function stackHtml(rows, noToggle) {
    let i = 0;
    function level(ind) {
      let h = '';
      while (i < rows.length && rows[i].indent === ind) {
        const r = rows[i++];
        let sub = '';
        if (i < rows.length && rows[i].indent > ind) sub = '<div class="tr-stack">' + level(ind + 1) + '</div>';
        h += '<div class="tr-item">' + cardHtml(r, { toggle: !noToggle, gen: r.badge, num: true }) + sub + '</div>';
      }
      return h;
    }
    return level(0);
  }

  function pickerHtml() {
    const mk = (isWide, isA) => roots.map((r, i) => (isA && (r.children || []).length < 5 ? '' :
      '<button type="button" class="tr-pill' + (picked === r.id && wide === isWide && wideA === !!isA ? ' on' : '') + '" data-pick="' + esc(r.id)
      + '"' + (isWide ? ' data-wide="1"' : '') + (isA ? ' data-variant="a"' : '') + ' title="' + esc(r.name)
      + (isA ? ' (lebar, G1 ke-4 dan ke-5 dipindah ke bawah G1 ke-3; cetak A3 portrait)' : isWide ? ' (lebar: G2 horizontal, G3 vertikal; cetak A3)' : '')
      + '">Tree ' + (i + 1) + (isA ? '.1a' : isWide ? '.1' : '') + '</button>')).join('');
    const pills = mk(false) + '<span class="tr-sep"></span>' + mk(true) + mk(true, true);
    const back = focusG1 ? '<a href="#" class="tr-back" data-unfocus="1">&laquo; Semua G1</a>' : '';
    return '<div class="tr-picker"><span>Pilih tree:</span>' + pills + back + '</div>';
  }

  // Legenda warna Tree n.1 (pengganti label G1/G2/G3), kotak di kanan bawah.
  function legendHtml() {
    const it = (cls, t) => '<div class="tr-lg-item"><span class="tr-lg-sw ' + cls + '"></span>' + t + '</div>';
    return '<div class="tr-legend"><div class="tr-lg-box"><div class="tr-lg-title">Keterangan</div>'
      + it('g1', 'G1 (generasi 1)') + it('g2', 'G2 (generasi 2)') + it('g3', 'G3 (generasi 3)') + '</div></div>';
  }

  // focusId: id G1 yang difokuskan (G1 lain hilang, G2 horizontal, G3+ vertikal); null = semua G1.
  function treeHtml(rootNode, open, focusId, wideAll, variantA) {
    const rootRow = { node: rootNode, id: rootNode.id, open: false, hasChildren: false, childCount: 0, partnerHitIds: [] };
    const g1Node = focusId ? (rootNode.children || []).find((c) => c.id === focusId) : null;
    let inner;
    if (wideAll) {
      // Tree n.1: semua G1 berjajar, G2 horizontal di bawah tiap G1, G3+ vertikal
      const mkGroup = (g1, asInner, extras) => {
        const outer = asInner === 'slot4' ? 'tr-wide tr-inner tr-slot tr-slot-4' : asInner === 'slot5' ? 'tr-wide tr-inner tr-slot tr-slot-5'
          : asInner ? 'tr-wide tr-inner' : 'tr-c tr-wide';
        const blk = M.buildColumns([g1], open, 1)[0];
        const g1Row = { node: g1, id: g1.id, gen: 1, open: false, hasChildren: false, childCount: 0, partnerHitIds: [] };
        // G1 dengan sedikit G2 (<= 3): satu kolom vertikal, G2 dan G3 bertumpuk di bawah G1
        if (blk.columns.length <= 3) {
          const g2Open = new Set((g1.children || []).map((c) => c.id));
          const vrows = M.childRows(g1, 1, g2Open);
          return '<div class="' + outer + ' tr-vgroup">' + cardHtml(g1Row, { toggle: false, extra: 'tr-g1card tr-g1wide', gen: 'G1', num: true })
            + (vrows.length ? '<div class="tr-stack tr-trunk tr-vg">' + stackHtml(vrows, true) + '</div>' : '') + '</div>';
        }
        const colsHtml = blk.columns.map((col) =>
          '<div class="tr-c">' + cardHtml(col.g1, { toggle: false, extra: 'tr-g1card', gen: 'G2', num: true })
          + (col.rows.length ? '<div class="tr-stack tr-trunk">' + stackHtml(col.rows) + '</div>' : '') + '</div>');
        // Tree n.1a: G1 ke-4 (kolom terakhir kiri, di bawah G2 terakhir) dan G1 ke-5 (kolom kanan) ditempel ke kolom G2 terakhir
        if (extras) {
          const n = colsHtml.length;
          const li = n % 2 ? n - 1 : n - 2;
          colsHtml[li] = colsHtml[li].replace(/<\/div>$/, extras.left + '</div>');
          if (n % 2) colsHtml.push('<div class="tr-c tr-xcol">' + extras.right + '</div>');
          else colsHtml[n - 1] = colsHtml[n - 1].replace(/<\/div>$/, extras.right + '</div>');
        }
        // G2: maksimal 2 kartu per baris, sisanya turun ke baris berikut; G3+ vertikal di bawah tiap G2
        let grid = '';
        for (let i = 0; i < colsHtml.length; i += 2) {
          const pair = colsHtml.slice(i, i + 2);
          if (pair.length === 1 && colsHtml.length > 1) pair.push('<div class="tr-c tr-ph"></div>');
          grid += '<div class="tr-row tr-g2row">' + pair.join('') + '</div>';
        }
        return '<div class="' + outer + '">' + cardHtml(g1Row, { toggle: false, extra: 'tr-g1card tr-g1wide', gen: 'G1', num: true })
          + (blk.columns.length ? '<div class="tr-stem tr-stem-c"></div><div class="tr-g2grid">' + grid + '</div>' : '') + '</div>';
      };
      const kids = rootNode.children || [];
      let cols;
      if (variantA && kids.length >= 5) {
        // Tree n.1a: G1 ke-4 dan ke-5 dipindah ke ruang kosong di bawah G1 ke-3
        cols = mkGroup(kids[0]) + mkGroup(kids[1])
          + '<div class="tr-c tr-wide tr-pcol">' + mkGroup(kids[2], true, { left: mkGroup(kids[3], 'slot4'), right: mkGroup(kids[4], 'slot5') }) + '</div>'
          + kids.slice(5).map((g) => mkGroup(g)).join('');
      } else {
        cols = kids.map((g) => mkGroup(g)).join('');
      }
      inner = cardHtml(rootRow, { toggle: false, extra: 'tr-rootcard tr-rootwide' })
        + ((rootNode.children || []).length ? '<div class="tr-stem"></div><div class="tr-row">' + cols + '</div>' : '');
    } else if (g1Node) {
      const block = M.buildColumns([g1Node], open, 1)[0];
      const g1Row = { node: g1Node, id: g1Node.id, gen: 1, open: false, hasChildren: false, childCount: 0, partnerHitIds: [] };
      const cols = block.columns.map((col) =>
        '<div class="tr-c">' + cardHtml(col.g1, { toggle: false, extra: 'tr-g1card', gen: 'G2', num: true })
        + (col.rows.length ? '<div class="tr-stack tr-trunk">' + stackHtml(col.rows) + '</div>' : '') + '</div>').join('');
      inner = cardHtml(rootRow, { toggle: false, extra: 'tr-rootcard' })
        + '<div class="tr-stem"></div>'
        + cardHtml(g1Row, { toggle: false, extra: 'tr-g1card clickable', gen: 'G1', num: true, unfocus: true })
        + (block.columns.length ? '<div class="tr-stem"></div><div class="tr-row">' + cols + '</div>' : '');
    } else {
      const block = M.buildColumns([rootNode], open)[0];
      const cols = block.columns.map((col) =>
        '<div class="tr-c">' + cardHtml(col.g1, { toggle: false, extra: 'tr-g1card clickable', gen: 'G1', num: true, focus: true })
        + (col.rows.length ? '<div class="tr-stack tr-trunk">' + stackHtml(col.rows) + '</div>' : '') + '</div>').join('');
      inner = cardHtml(rootRow, { toggle: false, extra: 'tr-rootcard' })
        + (block.columns.length ? '<div class="tr-stem"></div><div class="tr-row">' + cols + '</div>' : '');
    }
    return '<div class="tr-block"><div class="tr-body">'
      + (wideAll ? '' : '<div class="tr-ruler"></div>')
      + '<div class="tr-tree">' + inner + '</div></div>'
      + (wideAll ? legendHtml() : '') + '</div>';
  }

  function defaultHtml() {
    const sel = roots.filter((r) => r.id === picked);
    if (!sel.length) {
      return pickerHtml() + '<div class="tr-empty">Pilih Tree 1 sampai Tree ' + roots.length + ' untuk menampilkan tree.</div>';
    }
    return pickerHtml() + '<div class="tr-export">' + treeHtml(sel[0], openIds, focusG1, wide, wide && wideA) + '</div>';
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
              cardHtml({ node: k, id: k.id, gen: idx.byId.get(k.id).gen, open: false, hasChildren: false, childCount: 0, partnerHitIds: [] }, { extra: 'tr-sib' })).join('');
          } else {
            chip = '<span class="tr-chip" data-reveal="' + esc(r.id) + '">+ ' + r.hiddenSiblings + ' saudara</span>';
          }
        }
        const canOpen = r.hasChildren && r.focusChildren === 0;
        const open = canOpen && openIds.has(r.id);
        const row = Object.assign({}, r, { open });
        const kids = open
          ? '<div class="tr-stack tr-trunk">' + stackHtml(M.childRows(r.node, r.gen, openIds)) + '</div>' : '';
        return '<div class="tr-chainrow"><div class="tr-ruler"></div>'
          + '<div class="tr-chainbody" style="--g:' + r.gen + '"><div class="tr-chaininline">'
          + cardHtml(row, { path: true, toggle: canOpen, gen: r.ruler }) + chip + sibs + '</div>' + kids + '</div></div>';
      }).join('');
      return '<div class="tr-block"><div class="tr-block-head"><div class="tr-root-card">'
        + cardHtml(b.root, { path: true }) + '</div></div>' + rows + '</div>';
    }).join('') + '</div>';
  }

  // Label generasi (G1, G2, ...) di kolom penggaris kiri sejajar dengan kartu awal tiap kelompok,
  // plus garis putus-putus tipis ke kanan.
  function placeRulers(scope) {
    (scope || host).querySelectorAll('.tr-ruler').forEach((ruler) => {
      const cont = ruler.parentElement;
      ruler.querySelectorAll('.tr-glabel').forEach((e) => e.remove());
      cont.querySelectorAll(':scope > .tr-guide').forEach((e) => e.remove());
      const top = cont.getBoundingClientRect().top;
      const placed = [];
      cont.querySelectorAll('[data-gen]').forEach((el) => {
        const r = el.getBoundingClientRect();
        const y = r.top - top + r.height / 2;
        const gen = el.getAttribute('data-gen');
        // kolom berdampingan menghasilkan label generasi yang sama di tinggi hampir sama: satu saja
        const topY = r.top - top;
        if (placed.some((p) => p.gen === gen && Math.abs(p.t - topY) < 40)) return;
        placed.push({ gen, y, t: topY });
        const lab = document.createElement('div');
        lab.className = 'tr-glabel';
        lab.textContent = el.getAttribute('data-gen');
        lab.style.top = y + 'px';
        ruler.appendChild(lab);
        const g = document.createElement('div');
        g.className = 'tr-guide';
        g.style.top = y + 'px';
        cont.appendChild(g);
      });
    });
  }

  // Tree n.1a: G1 ke-5 diturunkan (zig-zag di bawah G1 ke-4) dan garis Root diteruskan di tepi kanan kolom
  // ke G1 ke-4 dan ke-5. Garis digambar dari posisi hasil tata letak.
  function layoutA(el) {
    if (!el) return;
    const pcol = el.querySelector('.tr-pcol');
    if (!pcol) return;
    const g4 = pcol.querySelector('.tr-slot-4');
    const g5 = pcol.querySelector('.tr-slot-5');
    if (!g4 || !g5) return;
    const had = el.classList.contains('tr-capturing');
    el.classList.add('tr-capturing');
    pcol.querySelectorAll('.tr-trunk-line').forEach((e) => e.remove());
    g5.style.marginTop = '0px';
    const c4 = g4.querySelector('.tr-g1wide');
    const c5 = g5.querySelector('.tr-g1wide');
    const gap = 26;
    const need = c4.getBoundingClientRect().bottom + gap - c5.getBoundingClientRect().top;
    g5.style.marginTop = Math.max(0, need) + 'px';
    const W = pcol.getBoundingClientRect();
    // batang di sisi kanan kartu paling kanan (bukan di belakangnya)
    let maxRight = 0;
    pcol.querySelectorAll('.tr-card').forEach((c) => { maxRight = Math.max(maxRight, c.getBoundingClientRect().right); });
    const xR = Math.min(W.width - 6, maxRight - W.left + 18);
    const line = (x, y, w, h) => {
      const d = document.createElement('div');
      d.className = 'tr-trunk-line';
      d.style.cssText = 'position:absolute;background:var(--ln);z-index:0;left:' + x + 'px;top:' + y + 'px;width:' + w + 'px;height:' + h + 'px';
      pcol.appendChild(d);
    };
    const wd = 3;
    const rel = (c) => { const r = c.getBoundingClientRect(); return { cx: r.left - W.left + r.width / 2, top: r.top - W.top }; };
    const a = rel(c4);
    const b = rel(c5);
    const ya = a.top - 19;   // tengah celah antara Dedy dan G1 ke-4
    const yb = b.top - 14;
    line(W.width / 2, 0, xR - W.width / 2 + wd, wd);      // bus Root diteruskan ke kanan
    line(xR, 0, wd, yb + wd);                              // batang di tepi kanan
    line(a.cx, ya, xR - a.cx + wd, wd);  line(a.cx, ya, wd, 19);   // cabang ke G1 ke-4
    line(b.cx, yb, xR - b.cx + wd, wd);  line(b.cx, yb, wd, 14);   // cabang ke G1 ke-5
    if (!had) el.classList.remove('tr-capturing');
  }

  // Tree n.1a: kartu Root dan batangnya digeser tepat di atas tengah kelompok ke-2 (G1 Mellie) agar garisnya lurus.
  function alignRoot(el) {
    if (!el) return;
    const root = el.querySelector('.tr-rootcard');
    const cols = el.querySelectorAll('.tr-tree > .tr-row > .tr-c');
    if (!root || !cols[1]) return;
    const had = el.classList.contains('tr-capturing');
    el.classList.add('tr-capturing');
    const stem = root.nextElementSibling;
    [root, stem].forEach((e) => { if (e) e.style.left = '0px'; });
    const rc = root.getBoundingClientRect();
    const mc = cols[1].getBoundingClientRect();
    const d = (mc.left + mc.width / 2) - (rc.left + rc.width / 2);
    [root, stem].forEach((e) => { if (e) { e.style.position = 'relative'; e.style.left = d + 'px'; } });
    if (!had) el.classList.remove('tr-capturing');
  }

  function paint(html) {
    const wrap = document.getElementById('tree-wrapper');
    const st = wrap ? [wrap.scrollTop, wrap.scrollLeft] : [0, 0];
    host.innerHTML = html;
    placeRulers();
    if (mode === 'default' && wide && wideA) { layoutA(host.querySelector('.tr-export')); alignRoot(host.querySelector('.tr-export')); }
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

  function reset() { openIds = new Set(); revealed = new Set(); focusG1 = null; wide = false; wideA = false; renderDefault(); }

  function onClick(e) {
    const rs = e.target.closest('[data-reset]');
    if (rs) { e.preventDefault(); const inp = document.getElementById('tree-search-input'); if (inp) inp.value = ''; reset(); return; }
    const pk = e.target.closest('[data-pick]');
    if (pk) { picked = pk.getAttribute('data-pick'); wide = pk.hasAttribute('data-wide'); wideA = pk.getAttribute('data-variant') === 'a'; openIds = new Set(); focusG1 = null; renderDefault(); return; }
    const uf = e.target.closest('[data-unfocus]');
    if (uf) { e.preventDefault(); focusG1 = null; openIds = new Set(); renderDefault(); return; }
    const fc = e.target.closest('[data-focus]');
    if (fc) { focusG1 = fc.getAttribute('data-focus'); openIds = new Set(); renderDefault(); return; }
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
  // Label tampilan saat satu G1 difokuskan (null bila tidak sedang fokus).
  function focusLabel() {
    if (mode !== 'default' || !focusG1 || !idx) return null;
    const f = idx.byId.get(focusG1);
    const t = roots.findIndex((r) => r.id === picked);
    return f ? 'Tree ' + (t + 1) + ' — Fokus G1: ' + f.node.name : null;
  }
  // Tata letak cetak Tree n.1: kelompok G1 dipecah jadi k baris berurutan (tiap baris punya bus sendiri
  // dengan penanda lanjutan dari akar) agar pohon lebih ringkas. Mengembalikan elemen ekspor.
  function printLayout(k) {
    rerender();
    const el = getExportElement();
    const tree = el.querySelector('.tr-tree');
    const row = tree && tree.querySelector(':scope > .tr-row');
    if (row && k > 1 && !wideA) {
      const rootName = (el.querySelector('.tr-rootcard .tr-name') || {}).textContent || '';
      const items = Array.from(row.children);
      const ws = items.map((i) => i.offsetWidth);
      const target = ws.reduce((a, b) => a + b, 0) / k;
      const rows = [[]];
      let acc = 0;
      items.forEach((it, i) => {
        if (rows[rows.length - 1].length && acc + ws[i] / 2 > target && rows.length < k) { rows.push([]); acc = 0; }
        rows[rows.length - 1].push(it);
        acc += ws[i];
      });
      rows.slice(1).forEach((grp) => {
        const cont = document.createElement('div');
        cont.className = 'tr-cont';
        cont.textContent = rootName + ' (lanjutan)';
        const stem = document.createElement('div');
        stem.className = 'tr-stem';
        const nr = document.createElement('div');
        nr.className = 'tr-row';
        grp.forEach((g) => nr.appendChild(g));
        tree.appendChild(cont);
        tree.appendChild(stem);
        tree.appendChild(nr);
      });
    }
    placeRulers(el);
    if (wideA) { layoutA(el); alignRoot(el); }
    return el;
  }
  // Legenda melayang di sudut kanan bawah pohon bila tidak menimpa kartu/kolom (menghemat tinggi halaman);
  // bila bertabrakan, legenda tetap di bawah pohon.
  function floatLegend(el) {
    const lg = el.querySelector('.tr-legend');
    if (!lg) return false;
    el.classList.add('tr-capturing');
    el.style.position = 'relative';
    lg.classList.add('tr-legend-float');
    const r = lg.firstElementChild.getBoundingClientRect();
    const hit = Array.from(el.querySelectorAll('.tr-card, .tr-c')).some((c) => {
      const b = c.getBoundingClientRect();
      return b.left < r.right + 8 && b.right > r.left - 8 && b.top < r.bottom + 8 && b.bottom > r.top - 8;
    });
    if (hit) { lg.classList.remove('tr-legend-float'); el.style.position = ''; }
    el.classList.remove('tr-capturing');
    return !hit;
  }
  // Label tampilan Tree n.1 (cetak A3); null bila tidak sedang tampil.
  function wideLabel() {
    if (mode !== 'default' || !wide || !picked) return null;
    const t = roots.findIndex((r) => r.id === picked);
    return 'Tree ' + (t + 1) + (wideA ? '.1a' : '.1') + ' — ' + roots[t].name;
  }
  function hasContent() { return !!host.querySelector('.tr-export'); }

  // Semua tree dalam keadaan default (tanpa cabang terbuka), masing-masing di wadah di luar layar untuk ditangkap.
  function buildDefaultExport() {
    const box = document.createElement('div');
    box.className = 'tr-offscreen';
    box.innerHTML = roots.map((r) => '<div class="tr-export">' + treeHtml(r, new Set()) + '</div>').join('');
    document.body.appendChild(box);
    placeRulers(box);
    const els = Array.from(box.querySelectorAll('.tr-export'));
    return {
      items: els.map((el, i) => ({ el, label: 'Tree ' + (i + 1) + ' — ' + roots[i].name })),
      dispose: () => box.remove(),
    };
  }

  root.SetfTreeView = { mount, renderDefault, renderFocus, reset, names, setTextScale, setSpacing, getExportElement, currentQuery, focusLabel, wideLabel, printLayout, floatLegend, hasContent, buildDefaultExport, rerender };
})(window);
