const fs = require("fs");
const esprima = require("esprima");

const html = fs.readFileSync("app/templates/payment_memo/index.html", "utf-8");
const scriptRegex = /<script.*?>([\s\S]*?)<\/script>/gi;
let match;
let hasSyntaxError = false;

while ((match = scriptRegex.exec(html)) !== null) {
    let js = match[1];
    js = js.replace(/\{\{.*?\}\}/g, '1');
    js = js.replace(/\{%[\s\S]*?%\}/g, '/* JINJA */');
    
    // pad with newlines
    let linesBefore = html.substring(0, match.index).split("\n").length;
    let paddedJs = "\n".repeat(linesBefore) + js;

    try {
        esprima.parseScript(paddedJs);
    } catch (e) {
        if (!e.description.includes("Unexpected token ?") && !e.description.includes("Unexpected identifier")) {
            console.log(`ERROR at line ${e.lineNumber}: ${e.description}`);
            hasSyntaxError = true;
        }
    }
}
if (!hasSyntaxError) {
    console.log("No syntax errors found (ignoring ?? and ?. compatibility)");
}
