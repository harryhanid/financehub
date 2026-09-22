function setfInjectDualYAxis(labels, datasets, scales) {
  let localLabels = labels.slice();
  localLabels.push("TOTAL");
  let newDatasets = [];

  const isStacked = scales && scales.y && scales.y.stacked;

  let stackTotalsLeft = {};
  let stackTotalsRight = {};
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
  
  console.log("maxLeft =", maxLeft, "maxRight =", maxRight);
}

setfInjectDualYAxis(["2020", "2021"], [
    { label: "A", data: [100, 200], stack: "S1" },
    { label: "B", data: [50, 150], stack: "S1" }
], { y: { stacked: true } });
