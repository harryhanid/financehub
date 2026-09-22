const fs = require('fs');

global.document = {
  querySelector: function(s) {
    console.log("querySelector:", s);
    if (s.includes("tbody")) {
      return { innerHTML: "" };
    }
    return null;
  },
  querySelectorAll: function(s) {
    return [];
  },
  getElementById: function(id) {
    console.log("getElementById:", id);
    return { 
      style: {},
      innerHTML: "",
      getContext: function() { return {}; }
    };
  }
};
global.window = { matchMedia: function() { return { matches: false }; } };
global.getComputedStyle = function() { return { getPropertyValue: function() { return ""; } }; };
global.Chart = class { constructor() {} destroy() {} };
global.ChartDataLabels = {};

global.SETF_STATUS_BADGE_CLASS = {};
global.fmtJutaan = function(n) { return String(n); };
global.showToast = function(msg) { console.log("TOAST:", msg); };

const code = fs.readFileSync('app/static/js/sahabat_etf.js', 'utf8');

try {
  eval(code);
} catch(e) {
  console.log("EVAL ERROR:", e);
}

const mockData = {
  kategori: [
    { cat1: 'Medical', budget: 100, payment: 0, realisasi: 50 },
    { cat1: 'Pendidikan', budget: 200, payment: 0, realisasi: 150 }
  ],
  yearly: [],
  pillar: [],
  over_budget: []
};

try {
  console.log("TESTING setfRenderDoughnutChart");
  setfRenderDoughnutChart("chart-kategori",
        mockData.kategori.map(function (k) { return k.cat1; }),
        mockData.kategori.map(function (k) { return k.realisasi; }),
        mockData.kategori.map(function (k) { return setfColorForCategory(k.cat1); }));
} catch(e) { console.log("ERROR in chart:", e); }

try {
  console.log("TESTING setfRenderKategoriTable");
  setfRenderKategoriTable(mockData.kategori);
} catch(e) { console.log("ERROR in table:", e); }
