const fs = require('fs');
const jsdom = require("jsdom");
const { JSDOM } = jsdom;

const html = `
<div id="setf-alert-container"></div>
<canvas id="chart-kategori"></canvas>
<table id="setf-kategori-table">
  <thead><tr><th>Kategori</th><th>Budget</th><th>Actual</th><th>Sisa</th></tr></thead>
  <tbody><tr><td colspan="6">Memuat data...</td></tr></tbody>
</table>
<table id="setf-pillar-table"><tbody></tbody></table>
`;

const dom = new JSDOM(html);
global.window = dom.window;
global.document = dom.window.document;
global.getComputedStyle = dom.window.getComputedStyle;

// Mock Chart
global.Chart = class { constructor() {} };
global.ChartDataLabels = {};

// Mock other dependencies
global.SETF_STATUS_BADGE_CLASS = {};
global.fmtJutaan = function(n) { return String(n); };

const code = fs.readFileSync('app/static/js/sahabat_etf.js', 'utf8');

try {
  eval(code);
} catch (e) {
  console.log("EVAL ERROR:", e);
}

const mockData = {
  kategori: [
    { cat1: 'Medical', budget: 100, payment: 0, realisasi: 50 },
    { cat1: 'Pendidikan', budget: 200, payment: 0, realisasi: 150 }
  ]
};

try {
  setfRenderKategoriTable(mockData.kategori);
  console.log("setfRenderKategoriTable OK!");
} catch (e) {
  console.log("setfRenderKategoriTable ERROR:", e);
}
