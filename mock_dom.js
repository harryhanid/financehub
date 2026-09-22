const fs = require('fs');

// Mock DOM
global.document = {
    querySelector: (selector) => {
        return {
            closest: () => ({ querySelector: () => ({ textContent: '' }) }),
            innerHTML: '',
            value: 'all',
            addEventListener: () => {}
        };
    },
    querySelectorAll: () => [],
    getElementById: (id) => ({})
};
global.window = { addEventListener: () => {} };
global.Chart = class { constructor() { this.destroy = () => {}; } };
global.setfCharts = {};
global.ChartDataLabels = {};

// Load target
const code = fs.readFileSync('app/static/js/sahabat_etf.js', 'utf8');

try {
    eval(code);
    
    // Mock data based on python backend response
    const mockData = {
        years: [2024, 2025],
        kategori: [
            { name: "By Medical", budget: [10, 20], realisasi: [5, 10] }
        ],
        pillar: [
            { name: "APP", budget: [50, 60], realisasi: [30, 40] }
        ]
    };
    
    setfRenderTahunanData(mockData);
    console.log("SUCCESS! No crashes in setfRenderTahunanData!");
} catch (e) {
    console.error("CRASH IN SCRIPT:", e);
}

