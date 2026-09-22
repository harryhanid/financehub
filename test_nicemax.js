function niceMax(val) {
    if (val <= 0) return 10;
    const order = Math.floor(Math.log10(val));
    const factor = Math.pow(10, order);
    const normalized = val / factor;
    let nice;
    if (normalized <= 1) nice = 1;
    else if (normalized <= 2) nice = 2;
    else if (normalized <= 2.5) nice = 2.5;
    else if (normalized <= 5) nice = 5;
    else nice = 10;
    return nice * factor;
}
console.log(niceMax(4546 * 1.5));
console.log(niceMax(7135 * 1.25));
