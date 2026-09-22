function setfInjectDualYAxis(labels, datasets, scales) {
  let localLabels = labels.slice();
  localLabels.push("TOTAL");
  let newDatasets = [];

  const isStacked = scales && scales.y && scales.y.stacked;

  let stackTotalsLeft = {};  // e.g., stackTotalsLeft["StackBudget"][dataIndex] = sum
  let stackTotalsRight = {}; // e.g., stackTotalsRight["StackBudget"] = sum
  let maxLeft = 0;
  let maxRight = 0;

  datasets.forEach(function(ds, dsIdx) {
    const dsClone = Object.assign({}, ds);
    dsClone.data = ds.data.slice();
    
    let sum = 0;
    dsClone.data.forEach(function(v, idx) { 
        if (typeof v === "number" && !isNaN(v)) {
            sum += v; 
            if (!isStacked) {
                if (v > maxLeft) maxLeft = v;
            } else {
                const stackId = ds.stack || "default";
                if (!stackTotalsLeft[stackId]) stackTotalsLeft[stackId] = [];
                stackTotalsLeft[stackId][idx] = (stackTotalsLeft[stackId][idx] || 0) + v;
                if (stackTotalsLeft[stackId][idx] > maxLeft) maxLeft = stackTotalsLeft[stackId][idx];
            }
        }
    });
    
    dsClone.data.push(null);
    newDatasets.push(dsClone);
    
    const shadowDs = Object.assign({}, dsClone);
    shadowDs.data = dsClone.data.map(() => null);
    shadowDs.data[shadowDs.data.length - 1] = sum;
    shadowDs.yAxisID = 'y-right';
    shadowDs.label = dsClone.label + " (Total)";
    
    if (shadowDs.backgroundColor) shadowDs.backgroundColor = shadowDs.backgroundColor;
    
    if (!isStacked) {
        if (sum > maxRight) maxRight = sum;
    } else {
        const stackId = ds.stack || "default";
        stackTotalsRight[stackId] = (stackTotalsRight[stackId] || 0) + sum;
        if (stackTotalsRight[stackId] > maxRight) maxRight = stackTotalsRight[stackId];
    }
    
    newDatasets.push(shadowDs);
  });

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  scales["y-right"] = {
    type: "linear", display: true, position: "right",
    title: { display: true, text: "Skala Total (Juta Rp)", color: isDark ? "#94a3b8" : "#64748b", font: {size: 10} },
    grid: { drawOnChartArea: false },
    ticks: {
      color: isDark ? "#94a3b8" : "#64748b",
      callback: function(value) { return setfFmtJutaan(value); }
    }
  };

  // Adjust suggestedMax to enforce visual illusion
  if (scales.y && !scales.y.suggestedMax) {
      scales.y.suggestedMax = maxLeft * 1.35; // Make left bars take up to ~74% height
  }
  scales["y-right"].suggestedMax = maxRight * 1.05; // Make right total bar take up to ~95% height

  return { labels: localLabels, datasets: newDatasets, scales: scales };
}
