const fs = require('fs');
const jsdom = require("jsdom");
const { JSDOM } = jsdom;

const html = `<!DOCTYPE html>
<html>
<body>
  <div id="setf-tahunan-kategori-table"><h3></h3><thead></thead><tbody></tbody></div>
  <div id="setf-tahunan-pillar-table"><h3></h3><thead></thead><tbody></tbody></div>
  <canvas id="chart-tahunan-kategori"></canvas>
  <canvas id="chart-tahunan-pillar"></canvas>
  <table id="setf-table"><tbody></tbody></table>
  <table id="setf-kategori-table"><tbody></tbody></table>
  <table id="setf-latest-payments-table"><tbody></tbody></table>
  <table id="setf-pillar-table"><tbody></tbody></table>
  <table id="setf-family-table"><tbody></tbody></table>
  <div id="setf-tahunan-kat-mode"><input type="radio" name="setf-tahunan-kat-mode" value="all" checked></div>
  <div id="setf-tahunan-pil-mode"><input type="radio" name="setf-tahunan-pil-mode" value="all" checked></div>
  <div id="setf-kat-mode"><input type="radio" name="setf-kat-mode" value="all" checked></div>
</body>
</html>`;

const dom = new JSDOM(html, { runScripts: "dangerously" });
const window = dom.window;
global.window = window;
global.document = window.document;
global.Chart = class Chart { constructor() { this.destroy = function(){}; } };
global.ChartDataLabels = {};

// Mock fetch
global.fetch = function() {
    return Promise.resolve({
        json: () => Promise.resolve({ rows: [], families: [] })
    });
};

const scriptCode = fs.readFileSync('app/static/js/sahabat_etf.js', 'utf-8');

try {
    window.eval(scriptCode);
    
    // Setup initial state
    window.setfYearlyData = {
        years: [2020, 2021],
        kategori: [{ name: "Medical", budget: [100, 200], realisasi: [50, 100] }],
        pillar: [{ name: "APP", budget: [100, 200], realisasi: [50, 100] }]
    };
    
    console.log("Calling setfRenderTahunanKategori...");
    window.setfRenderTahunanKategori();
    
    console.log("Calling setfRenderTahunanPillar...");
    window.setfRenderTahunanPillar();
    
    console.log("Success! No immediate runtime errors.");
} catch (e) {
    console.error("RUNTIME ERROR DETECTED:", e);
}
