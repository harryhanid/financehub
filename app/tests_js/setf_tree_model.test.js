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
