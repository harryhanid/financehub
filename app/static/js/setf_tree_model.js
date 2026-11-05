// Logika murni Tree Query Sahabat ETF (tanpa DOM) agar bisa dites dengan `node --test`.
(function (root) {
  function indexTree(roots) {
    const byId = new Map();
    const rootIds = [];
    function walk(node, parentId, gen) {
      byId.set(node.id, { node, parentId, gen });
      (node.children || []).forEach((c) => walk(c, node.id, gen + 1));
    }
    roots.forEach((r) => { rootIds.push(r.id); walk(r, null, 0); });
    return { byId, rootIds };
  }

  function nameMatches(node, q) {
    const self = (node.name || '').toLowerCase().includes(q);
    const partnerIds = (node.partners || [])
      .filter((p) => (p.name || '').toLowerCase().includes(q))
      .map((p) => p.id);
    return { self, partnerIds };
  }

  function bareFocus(node, gen) {
    return { node, gen, isHit: false, partnerHitIds: [], hiddenSiblings: 0, children: [] };
  }

  // Memangkas keluarga ke rantai leluhur -> hasil; null bila tak ada hasil di dalamnya.
  function pruneToHits(node, gen, q) {
    const m = nameMatches(node, q);
    const isHit = m.self || m.partnerIds.length > 0;
    const kids = node.children || [];
    const kept = [];
    kids.forEach((c) => {
      const f = pruneToHits(c, gen + 1, q);
      if (f) kept.push(f);
    });
    if (!isHit && kept.length === 0) return null;
    const out = { node, gen, isHit: m.self, partnerHitIds: m.partnerIds, hiddenSiblings: 0, children: [] };
    if (isHit && gen === 0) {
      // Akar yang cocok tampil dengan G1-nya; G1 yang punya hasil di bawahnya memakai rantai hasilnya.
      out.children = kids.map((c) => kept.find((k) => k.node === c) || bareFocus(c, gen + 1));
      return out;
    }
    // Hasil: anak-anaknya tertutup, kecuali yang membawa hasil lain di bawahnya.
    kept.forEach((f) => { f.hiddenSiblings = kids.length - kept.length; });
    out.children = kept;
    return out;
  }

  function searchFocus(roots, query) {
    const q = (query || '').trim().toLowerCase();
    if (!q) return null;
    const families = [];
    roots.forEach((r) => {
      const f = pruneToHits(r, 0, q);
      if (f) families.push(f);
    });
    return { families, shownFamilies: families.length, totalFamilies: roots.length };
  }

  function toggleOpen(openIds, id) {
    const next = new Set(openIds);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  }

  function makeRow(node, gen, indent, openIds, extra) {
    const kids = node.children || [];
    return Object.assign({
      id: node.id, node, gen, indent,
      hasChildren: kids.length > 0, childCount: kids.length,
      open: openIds.has(node.id), badge: null, ruler: null,
    }, extra || {});
  }

  // Kartu G2+ sebuah kolom: anak G1 selalu tampil; turunan lebih dalam hanya bila induknya terbuka.
  function stackRows(children, gen, indent, openIds, out) {
    children.forEach((c, i) => {
      const row = makeRow(c, gen, indent, openIds);
      if (i === 0) row.badge = 'G' + gen;
      out.push(row);
      if (row.open && row.hasChildren) stackRows(c.children, gen + 1, indent + 1, openIds, out);
    });
  }

  // base = 0: kolom = G1, tumpukan = G2+. base = 1 (fokus satu G1): kolom = G2, tumpukan = G3+.
  function buildColumns(roots, openIds, base) {
    const b = base || 0;
    return roots.map((root) => ({
      root,
      columns: (root.children || []).map((g1) => {
        const rows = [];
        stackRows(g1.children || [], 2 + b, 0, openIds, rows);
        return { g1: makeRow(g1, 1 + b, 0, openIds, { ruler: 'G' + (1 + b) }), rows };
      }),
    }));
  }

  // Kartu anak sebuah node (untuk membuka turunan hasil pencarian); turunan lebih dalam hanya bila terbuka.
  function childRows(node, gen, openIds) {
    const out = [];
    stackRows(node.children || [], gen + 1, 0, openIds, out);
    return out;
  }

  // Mode pencarian: rantai leluhur -> hasil, satu penggaris per generasi.
  function focusRows(families) {
    return families.map((fam) => {
      const none = new Set();
      const chain = [];
      const hits = [];
      const walk = (f) => {
        chain.push(makeRow(f.node, f.gen, f.gen - 1, none, {
          ruler: 'G' + f.gen, isHit: f.isHit, partnerHitIds: f.partnerHitIds, hiddenSiblings: f.hiddenSiblings,
          focusChildren: f.children.length,
        }));
        if (f.isHit || f.partnerHitIds.length) hits.push(f.node.id);
        f.children.forEach(walk);
      };
      fam.children.forEach(walk);
      const root = makeRow(fam.node, 0, 0, none, {
        isHit: fam.isHit, partnerHitIds: fam.partnerHitIds, hiddenSiblings: 0,
      });
      if (fam.isHit || fam.partnerHitIds.length) hits.unshift(fam.node.id);
      return { root, chain, hits };
    });
  }

  const BULAN = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];

  // WIB = UTC+7 tetap; dihitung dari UTC agar tidak bergantung zona waktu peramban.
  function formatPrintStamp(date) {
    const w = new Date(date.getTime() + 7 * 3600 * 1000);
    const p2 = (v) => String(v).padStart(2, '0');
    return 'Dicetak: ' + p2(w.getUTCDate()) + ' ' + BULAN[w.getUTCMonth()] + ' ' + w.getUTCFullYear()
      + ' ' + p2(w.getUTCHours()) + ':' + p2(w.getUTCMinutes()) + ' WIB';
  }

  // Dipas ke halaman: lebar konten memenuhi lebar halaman (tidak diperbesar melebihi opt.maxScale).
  // Bila tinggi melebihi satu halaman, konten dikecilkan sampai muat satu halaman selama skalanya
  // masih >= 60% dari skala fit-lebar; bila lebih tinggi lagi, dipotong per halaman pada skala fit-lebar.
  function slicePages(contentW, contentH, opt) {
    const usableH = opt.pageH - 2 * opt.margin - opt.headerH;
    const base = Math.min((opt.pageW - 2 * opt.margin) / contentW, opt.maxScale || Infinity);
    let scale = base;
    if (contentH * base > usableH) {
      const fitH = usableH / contentH;
      if (fitH >= 0.6 * base) scale = fitH;
    }
    const perPage = Math.max(1, Math.floor(usableH / scale));
    const slices = [];
    for (let sy = 0; sy < contentH; sy += perPage) {
      slices.push({ sy, sh: Math.min(perPage, contentH - sy) });
    }
    return { scale, slices };
  }

  // Pilih landscape atau portrait (A4) yang paling pas untuk ukuran konten: halaman paling sedikit,
  // lalu skala terbesar; bila seri, landscape.
  function pickLayout(contentW, contentH, opt) {
    const sizes = opt.paper === 'A3'
      ? [['landscape', 420, 297], ['portrait', 297, 420]]
      : [['landscape', 297, 210], ['portrait', 210, 297]];
    const cands = sizes.map(([orientation, pageW, pageH]) => {
      const r = slicePages(contentW, contentH, Object.assign({}, opt, { pageW, pageH }));
      return { orientation, pageW, pageH, scale: r.scale, slices: r.slices };
    });
    const [land, port] = cands;
    if (port.slices.length < land.slices.length) return port;
    if (port.slices.length === land.slices.length && port.scale > land.scale + 1e-9) return port;
    return land;
  }

  // Potongan horizontal untuk gambar yang terlalu lebar: tiap potongan <= maxW piksel, dipotong
  // di tepi kanan kolom (cols = [{l, r}]) agar kartu tidak terbelah. Mulai dari startX (setelah penggaris).
  function tileCuts(cols, startX, totalW, maxW, avoid) {
    const av = avoid || [];
    const rights = cols.map((c) => c.r).filter((x) => !av.some((a) => x > a.l + 1 && x < a.r - 1)).sort((a, b) => a - b);
    const out = [];
    let x0 = startX;
    while (x0 < totalW - 1) {
      const limit = x0 + maxW;
      if (totalW <= limit) { out.push({ sx: x0, sw: totalW - x0 }); break; }
      let cut = limit;
      for (let i = rights.length - 1; i >= 0; i--) {
        if (rights[i] <= limit && rights[i] > x0 + 1) { cut = rights[i]; break; }
      }
      out.push({ sx: x0, sw: cut - x0 });
      x0 = cut;
    }
    return out;
  }

  // Kotak pembatas piksel non-putih (RGBA) + padding, dipotong ke ukuran gambar; untuk memangkas ruang kosong PDF.
  function contentBounds(rgba, w, h, pad) {
    let left = w, top = h, right = -1, bottom = -1;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = (y * w + x) * 4;
        if (rgba[i + 3] > 0 && (rgba[i] < 250 || rgba[i + 1] < 250 || rgba[i + 2] < 250)) {
          if (x < left) left = x;
          if (x > right) right = x;
          if (y < top) top = y;
          if (y > bottom) bottom = y;
        }
      }
    }
    if (right < 0) return { left: 0, top: 0, right: w, bottom: h };
    return {
      left: Math.max(0, left - pad), top: Math.max(0, top - pad),
      right: Math.min(w, right + 1 + pad), bottom: Math.min(h, bottom + 1 + pad),
    };
  }

  const api = { tileCuts, contentBounds, pickLayout, indexTree, nameMatches, searchFocus, toggleOpen, buildColumns, childRows, focusRows, formatPrintStamp, slicePages };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SetfTreeModel = api;
})(typeof window !== 'undefined' ? window : globalThis);
