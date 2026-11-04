const test = require('node:test');
const assert = require('node:assert/strict');
const M = require('../static/js/setf_tree_model.js');

const n = (id, name, children = [], partners = [], extra = {}) =>
  ({ id, name, code: id, children, partners: partners.map(([pid, pname]) => ({ id: pid, name: pname })), ...extra });

function fixture() {
  return [
    n('A', 'Eka Tjipta', [
      n('A1', 'Trini Lasuki', [
        n('A1.1', 'Oei Tjie Goen', [], [['A1.1.A', 'Wenny Limantara']]),
        n('A1.2', 'Oei Hoei Beng', [
          n('A1.2.A.1', 'Winata Tanuwijaya', [
            n('A1.2.A.1.A.1', 'Olivia Tanuwijaya', [], [], { parent_partner_id: 'A1.2.A.1.A' }),
          ], [['A1.2.A.1.A', 'Erna Suriani']], { parent_partner_id: 'A1.2.A' }),
        ], [['A1.2.A', 'Tan Teng Hong']]),
        n('A1.3', 'Oei Hong Leong'),
        n('A1.4', 'Sukmawati Widjaja'),
      ]),
      n('A2', 'Mellie Pirieh', [n('A2.1', 'Nanny Widjaja')]),
    ]),
    n('B', 'Hea Sitaba', [n('B1', 'Giok')]),
  ];
}

const chainIds = (fn) => { const ids = []; let c = fn; while (c) { ids.push(c.node.id); c = c.children[0]; } return ids; };

test('indexTree memberi generasi dan induk', () => {
  const idx = M.indexTree(fixture());
  assert.equal(idx.byId.get('A').gen, 0);
  assert.equal(idx.byId.get('A1.2.A.1').gen, 3);
  assert.equal(idx.byId.get('A1.2.A.1').parentId, 'A1.2');
  assert.deepEqual(idx.rootIds, ['A', 'B']);
});

test('searchFocus null untuk query kosong atau spasi', () => {
  assert.equal(M.searchFocus(fixture(), '   '), null);
  assert.equal(M.searchFocus(fixture(), ''), null);
});

test('searchFocus membentuk rantai leluhur dan menyembunyikan saudara', () => {
  const r = M.searchFocus(fixture(), 'WINATA');
  assert.equal(r.shownFamilies, 1);
  assert.equal(r.totalFamilies, 2);
  const root = r.families[0];
  assert.deepEqual(chainIds(root), ['A', 'A1', 'A1.2', 'A1.2.A.1']);
  const a1 = root.children[0];
  assert.equal(a1.hiddenSiblings, 1);
  const a12 = a1.children[0];
  assert.equal(a12.hiddenSiblings, 3);
  const hit = a12.children[0];
  assert.equal(hit.isHit, true);
  assert.deepEqual(hit.children, []);
});

test('searchFocus menandai hasil di nama partner anak', () => {
  const hit = M.searchFocus(fixture(), 'erna').families[0].children[0].children[0].children[0];
  assert.equal(hit.node.id, 'A1.2.A.1');
  assert.equal(hit.isHit, false);
  assert.deepEqual(hit.partnerHitIds, ['A1.2.A.1.A']);
});

test('searchFocus menandai hasil di nama partner induk', () => {
  const hit = M.searchFocus(fixture(), 'tan teng').families[0].children[0].children[0];
  assert.equal(hit.node.id, 'A1.2');
  assert.deepEqual(hit.partnerHitIds, ['A1.2.A']);
});

test('searchFocus pada akar menampilkan akar dengan G1-nya', () => {
  const root = M.searchFocus(fixture(), 'eka').families[0];
  assert.equal(root.node.id, 'A');
  assert.equal(root.isHit, true);
  assert.deepEqual(root.children.map((c) => c.node.id), ['A1', 'A2']);
  assert.ok(root.children.every((c) => c.isHit === false && c.children.length === 0));
});

test('searchFocus tanpa hasil', () => {
  const r = M.searchFocus(fixture(), 'zzz');
  assert.deepEqual(r.families, []);
  assert.equal(r.shownFamilies, 0);
  assert.equal(r.totalFamilies, 2);
});

test('searchFocus hasil di beberapa keluarga', () => {
  const r = M.searchFocus(fixture(), 'g');
  assert.equal(r.shownFamilies, 2);
});

test('buildColumns tampilan awal: G1 berjajar, G2 bertumpuk, G3 tertutup', () => {
  const blocks = M.buildColumns(fixture(), new Set());
  const a = blocks[0];
  assert.equal(a.root.id, 'A');
  assert.deepEqual(a.columns.map((c) => c.g1.id), ['A1', 'A2']);
  assert.deepEqual(a.columns[0].rows.map((r) => r.id), ['A1.1', 'A1.2', 'A1.3', 'A1.4']);
  const a12 = a.columns[0].rows[1];
  assert.equal(a12.hasChildren, true);
  assert.equal(a12.childCount, 1);
  assert.equal(a12.open, false);
  assert.equal(a12.indent, 0);
});

test('buildColumns membuka cabang ke bawah dengan indentasi', () => {
  const col = M.buildColumns(fixture(), new Set(['A1.2']))[0].columns[0];
  assert.deepEqual(col.rows.map((r) => r.id), ['A1.1', 'A1.2', 'A1.2.A.1', 'A1.3', 'A1.4']);
  assert.equal(col.rows[2].indent, 1);
  assert.equal(col.rows[1].open, true);
});

test('lencana hanya di kelompok saudara >= 2 kartu', () => {
  const blocks = M.buildColumns(fixture(), new Set());
  assert.equal(blocks[0].columns[0].rows[0].badge, 'G2');
  assert.ok(blocks[0].columns[0].rows.slice(1).every((r) => r.badge === null));
  assert.equal(blocks[0].columns[1].rows[0].badge, null); // A2 hanya satu anak
  const open1 = M.buildColumns(fixture(), new Set(['A1.2']))[0].columns[0];
  assert.equal(open1.rows[2].badge, null); // satu anak -> tanpa lencana
  const f = fixture();
  f[0].children[0].children[1].children.push(n('A1.2.A.2', 'Elizabeth Tanuwijaya'));
  const open2 = M.buildColumns(f, new Set(['A1.2']))[0].columns[0];
  assert.equal(open2.rows[2].badge, 'G3');
  assert.equal(open2.rows[3].badge, null);
});

test('penggaris hanya melabeli baris G1 di tampilan awal', () => {
  const col = M.buildColumns(fixture(), new Set())[0].columns[0];
  assert.equal(col.g1.ruler, 'G1');
  assert.ok(col.rows.every((r) => r.ruler === null));
});

test('toggleOpen tidak memutasi Set asal dan bisa dibalik', () => {
  const s = new Set();
  const s2 = M.toggleOpen(s, 'A1.2');
  assert.equal(s.size, 0);
  assert.equal(s2.has('A1.2'), true);
  assert.equal(M.toggleOpen(s2, 'A1.2').has('A1.2'), false);
});

test('focusRows: rantai berpenggaris per generasi, akar tanpa penggaris', () => {
  const blocks = M.focusRows(M.searchFocus(fixture(), 'winata').families);
  assert.equal(blocks.length, 1);
  assert.equal(blocks[0].root.id, 'A');
  assert.equal(blocks[0].root.ruler, null);
  assert.deepEqual(blocks[0].chain.map((r) => r.id), ['A1', 'A1.2', 'A1.2.A.1']);
  assert.deepEqual(blocks[0].chain.map((r) => r.ruler), ['G1', 'G2', 'G3']);
  assert.deepEqual(blocks[0].hits, ['A1.2.A.1']);
  assert.ok(blocks[0].chain.every((r) => r.badge === null));
});

test('formatPrintStamp dalam WIB', () => {
  assert.equal(M.formatPrintStamp(new Date('2026-11-04T04:23:00Z')), 'Dicetak: 04 Nov 2026 11:23 WIB');
});

test('formatPrintStamp melewati tengah malam dan pergantian tahun', () => {
  assert.equal(M.formatPrintStamp(new Date('2026-12-31T18:05:00Z')), 'Dicetak: 01 Jan 2027 01:05 WIB');
});

test('slicePages memotong konten tinggi per halaman', () => {
  const r = M.slicePages(500, 1000, { pageW: 210, pageH: 297, margin: 10, headerH: 20 });
  assert.equal(r.scale, 0.38);
  assert.deepEqual(r.slices, [{ sy: 0, sh: 676 }, { sy: 676, sh: 324 }]);
});

test('slicePages: konten pendek satu halaman', () => {
  const r = M.slicePages(500, 300, { pageW: 210, pageH: 297, margin: 10, headerH: 20 });
  assert.deepEqual(r.slices, [{ sy: 0, sh: 300 }]);
});

test('searchFocus: hasil yang juga leluhur hasil lain tetap menampilkan hasil di bawahnya', () => {
  const f = fixture();
  f[0].children[0].children[1].children[0].children[0].name = 'Oei Olivia'; // A1.2.A.1.A.1
  const r = M.searchFocus(f, 'oei');
  const a1 = r.families[0].children[0];
  const a12 = a1.children.find((c) => c.node.id === 'A1.2');
  assert.equal(a12.isHit, true);
  const deep = a12.children[0].children[0];
  assert.equal(deep.node.id, 'A1.2.A.1.A.1');
  assert.equal(deep.isHit, true);
});

test('searchFocus: akar yang cocok menggabungkan G1 polos dengan rantai hasil', () => {
  const f = fixture();
  f[0].children[1].children[0].name = 'Eka Nanny'; // A2.1
  const root = M.searchFocus(f, 'eka').families[0];
  assert.equal(root.isHit, true);
  const a1 = root.children.find((c) => c.node.id === 'A1');
  const a2 = root.children.find((c) => c.node.id === 'A2');
  assert.deepEqual(a1.children, []);
  assert.deepEqual(a2.children.map((c) => c.node.id), ['A2.1']);
  assert.equal(a2.children[0].isHit, true);
});

test('childRows: anak sebuah node, turunan hanya bila dibuka', () => {
  const a12 = fixture()[0].children[0].children[1];
  const closed = M.childRows(a12, 2, new Set());
  assert.deepEqual(closed.map((r) => [r.id, r.gen, r.indent]), [['A1.2.A.1', 3, 0]]);
  const open = M.childRows(a12, 2, new Set(['A1.2.A.1']));
  assert.deepEqual(open.map((r) => [r.id, r.indent]), [['A1.2.A.1', 0], ['A1.2.A.1.A.1', 1]]);
});

test('focusRows: jumlah anak dalam rantai tercatat', () => {
  const b = M.focusRows(M.searchFocus(fixture(), 'winata').families)[0];
  assert.deepEqual(b.chain.map((r) => r.focusChildren), [1, 1, 0]);
});
